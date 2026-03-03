"""
flag_service.py

Business logic for flag review:
  - Retrieving flags with optional filters
  - Building context windows (surrounding rows) from stored dataset row data
  - Recording reviewer decisions and updating flag status
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import case, select, func
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.decision import Decision
from app.models.flag import Flag
from app.schemas.flags import (
    ContextRow,
    DecideResponse,
    DecisionRead,
    DecisionSubmit,
    FlagRead,
    FlagWithContext,
)

# Rows shown before and after the flagged row in the context window
CONTEXT_WINDOW = 3

# Maps reviewer action → flag status
_ACTION_TO_STATUS: dict[str, str] = {
    "confirmed": "confirmed",
    "rejected": "rejected",
    "overridden": "overridden",
}


# ── List helpers ───────────────────────────────────────────────────────────

def list_flags(
    db: Session,
    dataset_id: Optional[int] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    flag_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[Flag], int]:
    query = select(Flag)
    if dataset_id is not None:
        query = query.where(Flag.dataset_id == dataset_id)
    if status:
        query = query.where(Flag.status == status)
    if severity:
        query = query.where(Flag.severity == severity)
    if flag_type:
        query = query.where(Flag.flag_type == flag_type)

    # Sort: pending first, then by severity (high → medium → low), then by id
    severity_order = case(
        (Flag.severity == "high", 1),
        (Flag.severity == "medium", 2),
        (Flag.severity == "low", 3),
        else_=4,
    )
    status_order = case(
        (Flag.status == "pending", 1),
        else_=2,
    )
    query = query.order_by(status_order, severity_order, Flag.id)

    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    items = list(
        db.execute(query.offset((page - 1) * page_size).limit(page_size)).scalars().all()
    )
    return items, total


# ── Context retrieval ──────────────────────────────────────────────────────

def _build_context(dataset: Dataset, row_index: int) -> List[ContextRow]:
    """
    Extract up to CONTEXT_WINDOW rows before and after *row_index* from
    the dataset's stored row data.  Returns an empty list if no rows are
    available (e.g. legacy seed data that was not ingested through the
    upload endpoint).
    """
    stored: list[dict] = dataset.preview_rows or []
    if not stored:
        return []

    start = max(0, row_index - CONTEXT_WINDOW)
    end = min(len(stored), row_index + CONTEXT_WINDOW + 1)

    return [
        ContextRow(
            row_index=i,
            data=stored[i],
            is_flagged=(i == row_index),
        )
        for i in range(start, end)
        if i < len(stored)
    ]


def _latest_decision(db: Session, flag_id: int) -> Optional[Decision]:
    return (
        db.execute(
            select(Decision)
            .where(Decision.flag_id == flag_id)
            .order_by(Decision.decided_at.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )


# ── Public API ─────────────────────────────────────────────────────────────

def get_flag_with_context(db: Session, flag_id: int) -> Optional[FlagWithContext]:
    flag = db.get(Flag, flag_id)
    if flag is None:
        return None

    dataset = db.get(Dataset, flag.dataset_id)
    context = _build_context(dataset, flag.row_index) if dataset else []
    latest = _latest_decision(db, flag_id)

    return FlagWithContext(
        flag=FlagRead.model_validate(flag),
        context_rows=context,
        existing_decision=DecisionRead.model_validate(latest) if latest else None,
    )


def decide_flag(
    db: Session,
    flag_id: int,
    data: DecisionSubmit,
) -> Optional[DecideResponse]:
    """
    Record a reviewer decision, update the flag status, and return the
    updated flag + new decision record.  Returns None if flag not found.
    """
    flag = db.get(Flag, flag_id)
    if flag is None:
        return None

    decision = Decision(
        flag_id=flag_id,
        reviewer_name=data.reviewer_name,
        action=data.action,
        override_value=data.override_value,
        notes=data.notes,
    )
    db.add(decision)

    flag.status = _ACTION_TO_STATUS[data.action]
    db.commit()
    db.refresh(flag)
    db.refresh(decision)

    return DecideResponse(
        flag=FlagRead.model_validate(flag),
        decision=DecisionRead.model_validate(decision),
    )


# ── Decision log ───────────────────────────────────────────────────────────

def list_decision_log(
    db: Session,
    dataset_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[list, int]:
    """
    Return decisions joined with their parent flag for the audit log view.
    """
    query = (
        select(Decision, Flag)
        .join(Flag, Decision.flag_id == Flag.id)
        .order_by(Decision.decided_at.desc())
    )
    if dataset_id is not None:
        query = query.where(Flag.dataset_id == dataset_id)

    total_q = select(func.count()).select_from(query.subquery())
    total = db.execute(total_q).scalar_one()

    rows = db.execute(query.offset((page - 1) * page_size).limit(page_size)).all()

    from app.schemas.flags import DecisionLogEntry
    entries = [
        DecisionLogEntry(
            id=decision.id,
            flag_id=decision.flag_id,
            dataset_id=flag.dataset_id,
            column_name=flag.column_name,
            raw_value=flag.raw_value,
            proposed_value=flag.proposed_value,
            flag_type=flag.flag_type,
            severity=flag.severity,
            reviewer_name=decision.reviewer_name,
            action=decision.action,
            override_value=decision.override_value,
            notes=decision.notes,
            decided_at=decision.decided_at,
        )
        for decision, flag in rows
    ]
    return entries, total
