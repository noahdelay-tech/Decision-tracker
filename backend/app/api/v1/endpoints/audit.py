"""
audit.py  –  /api/v1/

POST /studies/{study_id}/export          generate a new 21 CFR Part 11 export
GET  /studies/{study_id}/exports         list prior exports
GET  /audit/exports/{export_ref}         fetch export record by ref
"""
from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.audit import AuditExportRead, ExportRequest, ExportResponse
from app.services import audit_service

router = APIRouter(tags=["audit"])


# ── per-study endpoints ──────────────────────────────────────────────────────

@router.post("/studies/{study_id}/export", response_model=ExportResponse, status_code=201)
def create_export(study_id: int, body: ExportRequest, db: Session = Depends(get_db)):
    result = audit_service.generate_export(
        db,
        study_id=study_id,
        exported_by=body.exported_by,
        reason=body.reason,
        export_format=body.export_format,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Study not found")
    audit_export, payload = result
    return ExportResponse(
        export=AuditExportRead.model_validate(audit_export),
        payload=payload,
    )


@router.get("/studies/{study_id}/exports", response_model=List[AuditExportRead])
def list_exports(study_id: int, db: Session = Depends(get_db)):
    return audit_service.list_exports(db, study_id)


# ── global audit lookup ──────────────────────────────────────────────────────

@router.get("/audit/exports/{export_ref}", response_model=AuditExportRead)
def get_export(export_ref: str, db: Session = Depends(get_db)):
    record = audit_service.get_export_by_ref(db, export_ref)
    if record is None:
        raise HTTPException(status_code=404, detail="Export not found")
    return record
