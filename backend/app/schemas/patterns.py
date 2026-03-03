from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class PatternRead(BaseModel):
    id: int
    sponsor_id: str
    flag_type: str
    column_name: str
    occurrence_count: int
    confirmation_rate: float
    common_override: Optional[str] = None
    example_reasonings: Optional[List[str]] = None
    last_updated: datetime

    model_config = {"from_attributes": True}


class PatternRebuildResponse(BaseModel):
    patterns_created: int
    patterns: List[PatternRead]
    rebuilt_at: datetime


# ── Structured study briefing ─────────────────────────────────────────────────

class ColumnRisk(BaseModel):
    """Per-column risk summary derived from pattern library."""
    column_name: str
    risk_level: str           # "high" | "medium" | "low"
    pattern_count: int        # distinct flag_types that affect this column
    total_occurrences: int    # sum of occurrence_count across all patterns
    dominant_flag_type: str   # flag_type with highest occurrence_count


class StudyBriefing(BaseModel):
    """
    Structured pre-study briefing produced from the pattern library.
    Contains no free text — all fields are machine-readable for UI rendering
    and optional LLM prompt construction.
    """
    sponsor_id: str
    study_type: str
    known_patterns: List[PatternRead]
    flagged_column_risks: List[ColumnRisk]
