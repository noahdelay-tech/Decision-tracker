from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, field_validator


# ── Context rows ──────────────────────────────────────────────────────────

class ContextRow(BaseModel):
    """A single row from the source dataset, with a flag indicator."""
    row_index: int
    data: Dict[str, Any]
    is_flagged: bool


# ── Flag read ─────────────────────────────────────────────────────────────

class FlagRead(BaseModel):
    id: int
    dataset_id: int
    row_index: int
    column_name: str
    raw_value: str
    proposed_value: Optional[str]
    flag_type: str
    severity: str           # low | medium | high
    biological_reasoning: str
    status: str             # pending | confirmed | rejected | overridden
    created_at: datetime

    model_config = {"from_attributes": True}


class FlagWithContext(BaseModel):
    """Flag detail with surrounding data rows and the most recent decision."""
    flag: FlagRead
    # ±CONTEXT_WINDOW rows centred on the flagged row; empty when no row data is stored
    context_rows: List[ContextRow]
    # The most recent reviewer decision, if any
    existing_decision: Optional[DecisionRead]


class FlagListResponse(BaseModel):
    items: List[FlagRead]
    total: int
    page: int
    page_size: int


# ── Decision I/O ──────────────────────────────────────────────────────────

class DecisionSubmit(BaseModel):
    """Input body for POST /flags/{flag_id}/decide."""
    reviewer_name: str
    action: str             # confirmed | rejected | overridden
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
    override_value: Optional[str]
    notes: Optional[str]
    decided_at: datetime

    model_config = {"from_attributes": True}


class DecisionLogEntry(BaseModel):
    """Decision row enriched with the flag's column and value for display."""
    id: int
    flag_id: int
    dataset_id: int
    column_name: str
    raw_value: str
    proposed_value: Optional[str]
    flag_type: str
    severity: str
    reviewer_name: str
    action: str
    override_value: Optional[str]
    notes: Optional[str]
    decided_at: datetime


class DecideResponse(BaseModel):
    """Response from the decide endpoint."""
    flag: FlagRead
    decision: DecisionRead


# Resolve the forward reference in FlagWithContext
FlagWithContext.model_rebuild()
