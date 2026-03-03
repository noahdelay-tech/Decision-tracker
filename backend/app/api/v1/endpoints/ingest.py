from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.ingest import IngestResponse
from app.services import ingest_service

router = APIRouter(prefix="/ingest", tags=["ingest"])

_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/", response_model=IngestResponse, status_code=201)
async def ingest_dataset(
    file: UploadFile = File(..., description="CSV or XLSX file to ingest"),
    study_id: int = Form(default=1, description="ID of the parent study"),
    db: Session = Depends(get_db),
) -> IngestResponse:
    """
    Upload a tabular data file, infer its biological column schema, and
    persist a Dataset record.

    - Accepts **.csv** and **.xlsx** / **.xls** files.
    - Performs a multi-step column-name normalisation + dictionary lookup
      to map raw column names to canonical biological variable names
      (e.g. `"BW"` → `body_weight`, `"ALT (U/L)"` → `alt`).
    - Stores the first 20 rows as a preview for the
      `GET /datasets/{dataset_id}` endpoint.
    """
    # ── Size guard ────────────────────────────────────────────────────────
    content = await file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {_MAX_UPLOAD_BYTES // (1024*1024)} MB.",
        )

    filename = file.filename or "upload"

    try:
        dataset, mappings, unmapped = ingest_service.create_dataset_from_upload(
            db=db,
            study_id=study_id,
            filename=filename,
            content=content,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return IngestResponse(
        dataset_id=dataset.id,
        study_id=dataset.study_id,
        filename=dataset.filename,
        row_count=dataset.row_count,  # type: ignore[arg-type]
        column_mappings=mappings,
        unmapped_columns=unmapped,
    )
