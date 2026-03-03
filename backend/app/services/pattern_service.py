"""
pattern_service.py

Clustering engine for the Institutional Memory pattern library.

Algorithm
─────────
1. Join decisions → flags → datasets → studies
2. Group by (sponsor_id, study_type, flag_type)
3. Per group:
   • Count actions  →  action_distribution
   • dominant_action = argmax
   • confidence     = max_count / total  (0–1)
   • common_override_values = up to 5 most-frequent non-null override values
   • rule_text      = plain-English sentence surfaced in briefings / UI
4. Upsert all patterns (delete-then-insert for simplicity with SQLite)
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.decision import Decision
from app.models.flag import Flag
from app.models.pattern import Pattern
from app.models.study import Study

# Minimum number of decisions before a pattern is emitted
MIN_SAMPLE_COUNT = 3

# Minimum fraction of decisions that must agree for a "definitive" rule
RULE_CONFIDENCE_THRESHOLD = 0.60


def _action_label(action: str) -> str:
    return {"confirmed": "confirmed as correct", "rejected": "rejected as a non-issue", "overridden": "overridden with a corrected value"}.get(action, action)


def _build_rule_text(
    sponsor_id: str,
    study_type: str,
    flag_type: str,
    dominant_action: str,
    confidence: float,
    sample_count: int,
    common_overrides: List[str],
) -> str:
    pct = int(confidence * 100)
    base = (
        f"For {sponsor_id}'s {study_type} studies, "
        f"{flag_type} flags are {_action_label(dominant_action)} "
        f"{pct}% of the time "
        f"(based on {sample_count} historical review{'s' if sample_count != 1 else ''})."
    )
    if dominant_action == "overridden" and common_overrides:
        top = ", ".join(f'"{v}"' for v in common_overrides[:3])
        base += f" Common corrected values: {top}."
    return base


# ── Public API ──────────────────────────────────────────────────────────────

def rebuild_patterns(db: Session) -> List[Pattern]:
    """
    Re-cluster ALL decisions in the database and regenerate the full
    pattern library.  Returns the list of upserted Pattern objects.
    """
    # Fetch every (decision, flag, dataset, study) tuple in one query
    rows = db.execute(
        select(Decision, Flag, Dataset, Study)
        .join(Flag,    Decision.flag_id    == Flag.id)
        .join(Dataset, Flag.dataset_id     == Dataset.id)
        .join(Study,   Dataset.study_id    == Study.id)
    ).all()

    # Accumulate counts grouped by clustering key
    # key → {action → count, "_overrides" → [values]}
    GroupKey = Tuple[str, str, str]
    groups: Dict[GroupKey, Dict] = defaultdict(lambda: defaultdict(int))

    for decision, flag, dataset, study in rows:
        key: GroupKey = (study.sponsor_id, study.study_type, flag.flag_type)
        groups[key][decision.action] += 1
        if decision.action == "overridden" and decision.override_value:
            groups[key].setdefault("_overrides", []).append(decision.override_value)

    # Delete existing patterns and rebuild
    db.execute(Pattern.__table__.delete())

    new_patterns: List[Pattern] = []
    for (sponsor_id, study_type, flag_type), counts in groups.items():
        # Build action distribution (exclude internal _overrides key)
        action_dist = {k: v for k, v in counts.items() if not k.startswith("_")}
        total = sum(action_dist.values())

        if total < MIN_SAMPLE_COUNT:
            continue

        dominant_action = max(action_dist, key=action_dist.__getitem__)
        confidence = action_dist[dominant_action] / total

        overrides: List[str] = counts.get("_overrides", [])  # type: ignore[assignment]
        top_overrides = [val for val, _ in Counter(overrides).most_common(5)]

        rule_text = _build_rule_text(
            sponsor_id, study_type, flag_type,
            dominant_action, confidence, total, top_overrides,
        )

        pattern = Pattern(
            sponsor_id=sponsor_id,
            study_type=study_type,
            flag_type=flag_type,
            sample_count=total,
            dominant_action=dominant_action,
            confidence=confidence,
            action_distribution=action_dist,
            common_override_values=top_overrides or None,
            rule_text=rule_text,
            last_rebuilt_at=datetime.utcnow(),
        )
        db.add(pattern)
        new_patterns.append(pattern)

    db.commit()
    for p in new_patterns:
        db.refresh(p)

    return new_patterns


def get_patterns_for_study(db: Session, study: Study) -> List[Pattern]:
    """Return all patterns matching this study's sponsor_id + study_type."""
    return list(
        db.execute(
            select(Pattern).where(
                Pattern.sponsor_id == study.sponsor_id,
                Pattern.study_type == study.study_type,
            ).order_by(Pattern.confidence.desc())
        ).scalars().all()
    )


def list_patterns(
    db: Session,
    sponsor_id: Optional[str] = None,
    study_type: Optional[str] = None,
    flag_type: Optional[str] = None,
) -> List[Pattern]:
    q = select(Pattern)
    if sponsor_id:
        q = q.where(Pattern.sponsor_id == sponsor_id)
    if study_type:
        q = q.where(Pattern.study_type == study_type)
    if flag_type:
        q = q.where(Pattern.flag_type == flag_type)
    return list(db.execute(q.order_by(Pattern.sponsor_id, Pattern.study_type, Pattern.confidence.desc())).scalars().all())
