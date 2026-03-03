"""
briefings.py  –  /api/v1/studies/{study_id}/...

GET  /studies/{study_id}/briefing             structured pattern-library briefing
GET  /studies/{study_id}/briefing/generate    Anthropic-generated plain-text briefing
GET  /studies/{study_id}/briefings            list historical LLM briefings
POST /studies/{study_id}/briefing/llm         return (or generate) LLM briefing
POST /studies/{study_id}/briefing/llm/refresh force-regenerate LLM briefing
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.study import Study
from app.schemas.briefing import BriefingRead
from app.schemas.patterns import ColumnRisk, PatternRead, StudyBriefing
from app.services import briefing_service
from briefing import generator as briefing_generator
from patterns.library import get_patterns_for_sponsor

router = APIRouter(prefix="/studies", tags=["briefings"])


# ── Anthropic-generated plain-text briefing ───────────────────────────────────

@router.get("/{study_id}/briefing/generate")
def generate_briefing(
    study_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
):
    """
    Return a plain-language study briefing written by the Anthropic API.

    The result is cached in the `briefings` table keyed by `study_id` and
    `model_used`.  Subsequent calls return the cached version unless
    `?force=true` is passed, which forces regeneration from scratch.

    Requires `ANTHROPIC_API_KEY` to be set in the `.env` file.
    """
    try:
        result = briefing_generator.generate_study_briefing(db, study_id, force=force)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if result is None:
        study = db.get(Study, study_id)
        if study is None:
            raise HTTPException(status_code=404, detail="Study not found")
        raise HTTPException(status_code=503, detail="Briefing generation returned no result")

    briefing_text, pattern_count = result
    return {"briefing_text": briefing_text, "pattern_count": pattern_count}


# ── Structured briefing (pattern-library powered) ─────────────────────────────

@router.get("/{study_id}/briefing", response_model=StudyBriefing)
def get_structured_briefing(study_id: int, db: Session = Depends(get_db)):
    """
    Structured pre-study briefing built from the pattern library.

    - **known_patterns** — all patterns for this sponsor_id ordered by
      occurrence_count descending.
    - **flagged_column_risks** — per-column risk summary ranked
      high / medium / low by total occurrences and distinct flag_type count.
    """
    study = db.get(Study, study_id)
    if study is None:
        raise HTTPException(status_code=404, detail="Study not found")

    patterns = get_patterns_for_sponsor(db, study.sponsor_id)

    # ── Build flagged_column_risks ────────────────────────────────────────────
    col_groups: Dict[str, list] = defaultdict(list)
    for p in patterns:
        col_groups[p.column_name].append(p)

    column_risks: List[ColumnRisk] = []
    for column_name, col_patterns in col_groups.items():
        total_occ   = sum(p.occurrence_count for p in col_patterns)
        pattern_cnt = len(col_patterns)
        dominant    = max(col_patterns, key=lambda p: p.occurrence_count)

        if total_occ >= 10 or pattern_cnt >= 3:
            risk = "high"
        elif total_occ >= 5 or pattern_cnt >= 2:
            risk = "medium"
        else:
            risk = "low"

        column_risks.append(ColumnRisk(
            column_name=column_name,
            risk_level=risk,
            pattern_count=pattern_cnt,
            total_occurrences=total_occ,
            dominant_flag_type=dominant.flag_type,
        ))

    risk_order = {"high": 0, "medium": 1, "low": 2}
    column_risks.sort(key=lambda r: (risk_order[r.risk_level], -r.total_occurrences))

    return StudyBriefing(
        sponsor_id=study.sponsor_id,
        study_type=study.study_type,
        known_patterns=[PatternRead.model_validate(p) for p in patterns],
        flagged_column_risks=column_risks,
    )


# ── LLM briefing (text) ───────────────────────────────────────────────────────

@router.post("/{study_id}/briefing/llm", response_model=BriefingRead)
def get_llm_briefing(study_id: int, db: Session = Depends(get_db)):
    """Return the cached LLM briefing text, or generate one on the fly."""
    briefing = briefing_service.generate_briefing(db, study_id, force_regenerate=False)
    if briefing is None:
        raise HTTPException(status_code=404, detail="Study not found")
    return briefing


@router.post("/{study_id}/briefing/llm/refresh", response_model=BriefingRead)
def refresh_llm_briefing(study_id: int, db: Session = Depends(get_db)):
    """Force-regenerate the LLM briefing."""
    briefing = briefing_service.generate_briefing(db, study_id, force_regenerate=True)
    if briefing is None:
        raise HTTPException(status_code=404, detail="Study not found")
    return briefing


@router.get("/{study_id}/briefings", response_model=List[BriefingRead])
def list_briefings(study_id: int, db: Session = Depends(get_db)):
    """List all historical LLM briefings for a study, newest first."""
    return briefing_service.list_briefings(db, study_id)
