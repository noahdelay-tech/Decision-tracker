"""
patterns.py  –  /api/v1/patterns/

GET  /patterns/          list patterns (filterable by sponsor_id, flag_type, column_name)
POST /patterns/rebuild   re-aggregate all confirmed/overridden decisions
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.patterns import PatternRead, PatternRebuildResponse
from patterns.library import build_pattern_library, list_patterns

router = APIRouter(prefix="/patterns", tags=["patterns"])


@router.get("/", response_model=List[PatternRead])
def get_patterns(
    sponsor_id:  Optional[str] = None,
    flag_type:   Optional[str] = None,
    column_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Return all patterns, optionally filtered.

    Query params: `sponsor_id`, `flag_type`, `column_name`
    """
    return list_patterns(db, sponsor_id=sponsor_id, flag_type=flag_type, column_name=column_name)


@router.post("/rebuild", response_model=PatternRebuildResponse)
def rebuild_patterns(db: Session = Depends(get_db)):
    """
    Re-aggregate all confirmed and overridden decisions into the pattern library.

    Clears the patterns table and inserts fresh rows.  Safe to call repeatedly.
    """
    patterns = build_pattern_library(db)
    return PatternRebuildResponse(
        patterns_created=len(patterns),
        patterns=[PatternRead.model_validate(p) for p in patterns],
        rebuilt_at=datetime.utcnow(),
    )
