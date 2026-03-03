from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator


# ── Study ─────────────────────────────────────────────────────────────────

class StudyRead(BaseModel):
    id: int
    name: str
    sponsor_id: str
    study_type: str
    species: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Dataset ───────────────────────────────────────────────────────────────

class DatasetRead(BaseModel):
    id: int
    study_id: int
    filename: str
    upload_status: str
    row_count: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Flag ──────────────────────────────────────────────────────────────────

class FlagRead(BaseModel):
    id: int
    dataset_id: int
    row_index: int
    column_name: str
    raw_value: str
    proposed_value: Optional[str] = None
    flag_type: str
    severity: str
    biological_reasoning: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Decision ──────────────────────────────────────────────────────────────

class DecisionCreate(BaseModel):
    flag_id: int
    reviewer_name: str
    action: str
    override_value: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        allowed = {"confirmed", "rejected", "overridden"}
        if v not in allowed:
            raise ValueError(f"action must be one of {allowed}")
        return v


class DecisionRead(BaseModel):
    id: int
    flag_id: int
    reviewer_name: str
    action: str
    override_value: Optional[str] = None
    notes: Optional[str] = None
    decided_at: datetime

    model_config = {"from_attributes": True}


# ── Shared list wrapper ───────────────────────────────────────────────────

class PagedResponse(BaseModel):
    items: List[FlagRead]
    total: int
    page: int
    page_size: int
