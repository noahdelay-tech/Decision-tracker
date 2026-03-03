from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.flag import Flag
from app.schemas.flags import (
    DecideResponse,
    DecisionLogEntry,
    DecisionSubmit,
    FlagListResponse,
    FlagWithContext,
)
from app.services import flag_service

router = APIRouter(prefix="/flags", tags=["flags"])


# ── Dataset progress (static path — must appear before /{flag_id}) ─────────

@router.get("/progress", response_model=Dict[str, Any])
def get_progress(
    dataset_id: int = Query(..., description="Dataset to compute progress for"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Review progress statistics for a single dataset.
    Returns: { total, pending, decided, percent_complete, by_status }
    """
    rows = db.execute(
        select(Flag.status, func.count().label("n"))
        .where(Flag.dataset_id == dataset_id)
        .group_by(Flag.status)
    ).all()

    counts: Dict[str, int] = {status: n for status, n in rows}
    total   = sum(counts.values())
    pending = counts.get("pending", 0)
    decided = total - pending

    return {
        "dataset_id":       dataset_id,
        "total":            total,
        "pending":          pending,
        "decided":          decided,
        "percent_complete": round(decided / total * 100) if total > 0 else 0,
        "by_status":        counts,
    }


# ── Flag list ──────────────────────────────────────────────────────────────

@router.get("/", response_model=FlagListResponse)
def list_flags(
    dataset_id: Optional[int] = Query(None, description="Filter by dataset"),
    status: Optional[str] = Query(None, description="pending | confirmed | rejected | overridden"),
    severity: Optional[str] = Query(None, description="low | medium | high"),
    flag_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> FlagListResponse:
    """
    List flags, sorted by pending-first then severity (high → low).

    Supports filtering by dataset, status, severity, and flag_type.
    """
    items, total = flag_service.list_flags(
        db,
        dataset_id=dataset_id,
        status=status,
        severity=severity,
        flag_type=flag_type,
        page=page,
        page_size=page_size,
    )
    return FlagListResponse(items=items, total=total, page=page, page_size=page_size)


# ── Flag detail with context ───────────────────────────────────────────────

@router.get("/{flag_id}", response_model=FlagWithContext)
def get_flag(flag_id: int, db: Session = Depends(get_db)) -> FlagWithContext:
    """
    Return a single flag together with:
    - **context_rows**: up to ±3 surrounding data rows (flagged row highlighted)
    - **existing_decision**: the most recent reviewer decision, if any
    """
    result = flag_service.get_flag_with_context(db, flag_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Flag id={flag_id} not found.")
    return result


# ── Submit a review decision ───────────────────────────────────────────────

@router.post("/{flag_id}/decide", response_model=DecideResponse, status_code=201)
def decide_flag(
    flag_id: int,
    body: DecisionSubmit,
    db: Session = Depends(get_db),
) -> DecideResponse:
    """
    Record a reviewer decision for a flag and update its status.

    - **confirmed** – flag is valid; no value change
    - **rejected**  – flag is not valid; no action needed
    - **overridden** – reviewer supplies a corrected value via `override_value`

    Every call writes a new `Decision` row (full audit trail). The flag's
    `status` is updated to match the action.
    """
    result = flag_service.decide_flag(db, flag_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Flag id={flag_id} not found.")
    return result


# ── Decision audit log ─────────────────────────────────────────────────────

@router.get("/decisions/log", response_model=List[DecisionLogEntry])
def decision_log(
    dataset_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[DecisionLogEntry]:
    """
    Full audit log of every reviewer decision, newest-first.

    Includes flag context (column, raw_value, flag_type, severity) alongside
    the decision metadata for export and compliance review.
    """
    entries, _ = flag_service.list_decision_log(db, dataset_id=dataset_id, page=page, page_size=page_size)
    return entries
