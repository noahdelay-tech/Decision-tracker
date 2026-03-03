"""
patterns/library.py
═══════════════════
Standalone pattern-library builder.

Algorithm
─────────
1. Query every **confirmed** or **overridden** decision joined through
   flags → datasets → studies.

2. Group rows by the triple  (sponsor_id, flag_type, column_name).

3. For each group compute:
     occurrence_count   – total decisions in this group
     confirmation_rate  – fraction whose action == "confirmed"
     common_override    – mode of override_value (overridden rows only)
     example_reasonings – up to 3 distinct biological_reasoning strings

4. Truncate the patterns table and insert fresh rows.

Can be imported by the FastAPI app **or** run directly:

    cd backend
    python -m patterns.library          # uses DATABASE_URL env var or default
    python -m patterns.library --reset  # same, but prints a summary
"""
from __future__ import annotations

import sys
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

# ── Types ────────────────────────────────────────────────────────────────────

_GroupKey = Tuple[str, str, str]  # (sponsor_id, flag_type, column_name)

_Row = Tuple[Decision, Flag, Dataset, Study]


# ── Core logic ───────────────────────────────────────────────────────────────

def _query_eligible_decisions(db: Session) -> List[_Row]:
    """Return all confirmed + overridden decisions with their joined context."""
    return db.execute(
        select(Decision, Flag, Dataset, Study)
        .join(Flag,    Decision.flag_id    == Flag.id)
        .join(Dataset, Flag.dataset_id     == Dataset.id)
        .join(Study,   Dataset.study_id    == Study.id)
        .where(Decision.action.in_(["confirmed", "overridden"]))
        .order_by(Decision.decided_at)
    ).all()


def _aggregate(rows: List[_Row]) -> Dict[_GroupKey, dict]:
    """Group rows and compute per-group statistics."""
    groups: Dict[_GroupKey, List[_Row]] = defaultdict(list)
    for row in rows:
        decision, flag, dataset, study = row
        key: _GroupKey = (study.sponsor_id, flag.flag_type, flag.column_name)
        groups[key].append(row)

    aggregated: Dict[_GroupKey, dict] = {}
    for key, items in groups.items():
        total     = len(items)
        confirmed = sum(1 for d, *_ in items if d.action == "confirmed")

        overrides = [
            d.override_value
            for d, *_ in items
            if d.action == "overridden" and d.override_value
        ]
        common_override: Optional[str] = (
            Counter(overrides).most_common(1)[0][0] if overrides else None
        )

        seen_reasonings: List[str] = []
        for _, flag, *_ in items:
            if flag.biological_reasoning and flag.biological_reasoning not in seen_reasonings:
                seen_reasonings.append(flag.biological_reasoning)
            if len(seen_reasonings) == 3:
                break

        aggregated[key] = {
            "occurrence_count":   total,
            "confirmation_rate":  round(confirmed / total, 4),
            "common_override":    common_override,
            "example_reasonings": seen_reasonings or None,
        }

    return aggregated


def build_pattern_library(db: Session) -> List[Pattern]:
    """
    Rebuild the entire pattern library from confirmed/overridden decisions.

    Clears the patterns table and inserts fresh rows.
    Returns the list of newly created Pattern objects.
    """
    rows       = _query_eligible_decisions(db)
    aggregated = _aggregate(rows)

    # Atomic clear-and-replace
    db.execute(Pattern.__table__.delete())

    new_patterns: List[Pattern] = []
    for (sponsor_id, flag_type, column_name), stats in aggregated.items():
        p = Pattern(
            sponsor_id=sponsor_id,
            flag_type=flag_type,
            column_name=column_name,
            occurrence_count=stats["occurrence_count"],
            confirmation_rate=stats["confirmation_rate"],
            common_override=stats["common_override"],
            example_reasonings=stats["example_reasonings"],
            last_updated=datetime.utcnow(),
        )
        db.add(p)
        new_patterns.append(p)

    db.commit()
    for p in new_patterns:
        db.refresh(p)

    return new_patterns


def get_patterns_for_sponsor(db: Session, sponsor_id: str) -> List[Pattern]:
    """Return all patterns for a given sponsor, ordered by occurrence_count desc."""
    return list(
        db.execute(
            select(Pattern)
            .where(Pattern.sponsor_id == sponsor_id)
            .order_by(Pattern.occurrence_count.desc())
        ).scalars().all()
    )


def list_patterns(
    db: Session,
    sponsor_id: Optional[str] = None,
    flag_type:  Optional[str] = None,
    column_name: Optional[str] = None,
) -> List[Pattern]:
    """Filterable pattern list for the GET /patterns endpoint."""
    q = select(Pattern)
    if sponsor_id:
        q = q.where(Pattern.sponsor_id == sponsor_id)
    if flag_type:
        q = q.where(Pattern.flag_type == flag_type)
    if column_name:
        q = q.where(Pattern.column_name == column_name)
    return list(
        db.execute(q.order_by(Pattern.sponsor_id, Pattern.occurrence_count.desc())).scalars().all()
    )


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_url = os.getenv("DATABASE_URL", "sqlite:///./data/decisiontracker.db")
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)

    db = SessionLocal()
    try:
        patterns = build_pattern_library(db)
        print(f"Pattern library rebuilt: {len(patterns)} pattern(s)")
        for p in patterns:
            print(
                f"  [{p.sponsor_id}] {p.flag_type} / {p.column_name}"
                f"  n={p.occurrence_count}"
                f"  confirm={p.confirmation_rate:.0%}"
                + (f"  override→{p.common_override!r}" if p.common_override else "")
            )
    finally:
        db.close()
