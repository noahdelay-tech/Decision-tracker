from __future__ import annotations

import csv
import io
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.dataset import Dataset
from app.models.decision import Decision
from app.models.flag import Flag
from app.schemas.ingest import DatasetDetailResponse, DatasetSummary
from app.services.ingest_service import PREVIEW_ROWS

router = APIRouter(prefix="/datasets", tags=["datasets"])

_AUDIT_COLUMNS = [
    "flag_id",
    "row_index",
    "column_name",
    "raw_value",
    "proposed_value",
    "flag_type",
    "severity",
    "biological_reasoning",
    "decision_action",
    "override_value",
    "reviewer_name",
    "decided_at",
]


@router.get("/", response_model=List[DatasetSummary])
def list_datasets(db: Session = Depends(get_db)) -> List[DatasetSummary]:
    """Return lightweight metadata for every dataset (no row data)."""
    rows = db.execute(select(Dataset).order_by(Dataset.created_at.desc())).scalars().all()
    return [
        DatasetSummary(
            id=d.id,
            study_id=d.study_id,
            filename=d.filename,
            upload_status=d.upload_status,
            row_count=d.row_count,
            column_count=len(d.column_mappings) + len(d.unmapped_columns)
            if d.column_mappings is not None and d.unmapped_columns is not None
            else None,
            created_at=d.created_at,
        )
        for d in rows
    ]


@router.get("/{dataset_id}/export/audit")
def export_audit_csv(dataset_id: int, db: Session = Depends(get_db)) -> StreamingResponse:
    """
    Generate a CSV audit trail for a completed dataset review.

    Only flags that have received a decision (confirmed / rejected / overridden)
    are included.  When a flag has multiple decisions, the most recent one is used.
    Rows are sorted by decided_at ascending.

    Response headers trigger a file download in the browser:
        Content-Disposition: attachment; filename="egret_audit_{dataset_id}_{date}.csv"
    """
    dataset: Dataset | None = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset id={dataset_id} not found.")

    # Fetch all decisions for flags in this dataset (decided flags only),
    # ordered ascending so later assignments overwrite earlier ones in the dict.
    rows = (
        db.execute(
            select(Flag, Decision)
            .join(Decision, Decision.flag_id == Flag.id)
            .where(Flag.dataset_id == dataset_id, Flag.status != "pending")
            .order_by(Decision.decided_at.asc())
        )
        .all()
    )

    # Keep only the latest decision per flag (last write wins since we sort asc)
    latest: dict[int, tuple[Flag, Decision]] = {}
    for flag, decision in rows:
        latest[flag.id] = (flag, decision)

    # Re-sort the deduped results by decided_at ascending
    decided = sorted(latest.values(), key=lambda pair: pair[1].decided_at)

    # Build CSV in memory
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_AUDIT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for flag, decision in decided:
        writer.writerow(
            {
                "flag_id": flag.id,
                "row_index": flag.row_index,
                "column_name": flag.column_name,
                "raw_value": flag.raw_value,
                "proposed_value": flag.proposed_value or "",
                "flag_type": flag.flag_type,
                "severity": flag.severity,
                "biological_reasoning": flag.biological_reasoning,
                "decision_action": decision.action,
                "override_value": decision.override_value or "",
                "reviewer_name": decision.reviewer_name,
                "decided_at": decision.decided_at.isoformat(),
            }
        )

    filename = f"egret_audit_{dataset_id}_{date.today().isoformat()}.csv"
    buf.seek(0)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{dataset_id}/detect")
def detect_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """
    Mark a dataset upload as complete and return its flag summary.

    Called automatically by the frontend after a successful ingest to
    transition the dataset status from 'processing' → 'complete'.
    """
    dataset: Dataset | None = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset id={dataset_id} not found.")

    dataset.upload_status = "complete"
    db.commit()
    db.refresh(dataset)

    flag_count = (
        db.execute(
            select(func.count(Flag.id)).where(Flag.dataset_id == dataset_id)
        ).scalar()
        or 0
    )
    pending_count = (
        db.execute(
            select(func.count(Flag.id)).where(
                Flag.dataset_id == dataset_id, Flag.status == "pending"
            )
        ).scalar()
        or 0
    )

    return {
        "dataset_id": dataset_id,
        "status": dataset.upload_status,
        "flag_count": flag_count,
        "pending_count": pending_count,
    }


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)) -> DatasetDetailResponse:
    """
    Return metadata and a row preview for a single dataset.

    - **metadata**: id, study_id, filename, upload_status, row_count,
      column_mappings, unmapped_columns, created_at
    - **preview**: first 20 rows captured at ingest time, keyed by
      original column names from the source file
    """
    dataset: Dataset | None = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset id={dataset_id} not found.")

    all_rows = dataset.preview_rows or []
    return DatasetDetailResponse(
        id=dataset.id,
        study_id=dataset.study_id,
        filename=dataset.filename,
        upload_status=dataset.upload_status,
        row_count=dataset.row_count,
        column_mappings=dataset.column_mappings,
        unmapped_columns=dataset.unmapped_columns,
        created_at=dataset.created_at,
        preview=all_rows[:PREVIEW_ROWS],
    )
