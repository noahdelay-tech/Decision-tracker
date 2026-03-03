"""
audit_service.py

21 CFR Part 11-aligned audit trail generation.

Each export is:
  • Timestamped  — exported_at (ISO 8601 UTC)
  • Identified   — export_ref (UUID4)
  • Signed       — SHA-256 of canonical JSON payload stored alongside the record
  • Attributed   — exported_by (reviewer name)
  • Immutable    — records are never modified; re-exports create new rows

Export payload structure (JSON)
────────────────────────────────
{
  "export_metadata": {
    "export_ref":     "<uuid4>",
    "study_id":       N,
    "study_name":     "…",
    "sponsor_id":     "…",
    "study_type":     "…",
    "exported_by":    "…",
    "exported_at":    "YYYY-MM-DDTHH:MM:SSZ",
    "record_count":   N,
    "system_version": "decision-tracker/1.0",
    "reason":         "…",
    "content_hash":   "<sha256 of records array>"
  },
  "records": [
    {
      "decision_id":       N,
      "flag_id":           N,
      "dataset_id":        N,
      "row_index":         N,
      "column_name":       "…",
      "raw_value":         "…",
      "proposed_value":    "…",
      "flag_type":         "…",
      "severity":          "…",
      "biological_reasoning": "…",
      "reviewer_name":     "…",
      "action":            "confirmed|rejected|overridden",
      "override_value":    "…",
      "notes":             "…",
      "decided_at":        "YYYY-MM-DDTHH:MM:SSZ"
    },
    …
  ]
}
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_export import AuditExport
from app.models.dataset import Dataset
from app.models.decision import Decision
from app.models.flag import Flag
from app.models.study import Study

SYSTEM_VERSION = "decision-tracker/1.0"


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_records(rows: List[Tuple]) -> List[Dict[str, Any]]:
    records = []
    for decision, flag, dataset, study in rows:
        records.append({
            "decision_id":           decision.id,
            "flag_id":               flag.id,
            "dataset_id":            dataset.id,
            "dataset_filename":      dataset.filename,
            "study_id":              study.id,
            "study_name":            study.name,
            "sponsor_id":            study.sponsor_id,
            "study_type":            study.study_type,
            "species":               study.species,
            "row_index":             flag.row_index,
            "column_name":           flag.column_name,
            "raw_value":             flag.raw_value,
            "proposed_value":        flag.proposed_value,
            "flag_type":             flag.flag_type,
            "severity":              flag.severity,
            "biological_reasoning":  flag.biological_reasoning,
            "flag_status":           flag.status,
            "reviewer_name":         decision.reviewer_name,
            "action":                decision.action,
            "override_value":        decision.override_value,
            "notes":                 decision.notes,
            "decided_at":            _iso(decision.decided_at),
            "flag_created_at":       _iso(flag.created_at),
        })
    return records


def _hash_records(records: List[Dict[str, Any]]) -> str:
    """SHA-256 of canonical (sorted-key) JSON representation of records list."""
    canonical = json.dumps(records, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


# ── Public API ───────────────────────────────────────────────────────────────

def generate_export(
    db: Session,
    study_id: int,
    exported_by: str,
    reason: str = "routine_audit",
    export_format: str = "json",
) -> Optional[Tuple[AuditExport, Dict[str, Any]]]:
    """
    Create a new immutable audit export for *study_id*.
    Returns (AuditExport ORM object, full payload dict) or None if study
    not found.
    """
    study = db.get(Study, study_id)
    if study is None:
        return None

    # Fetch all decided flags for this study
    rows = db.execute(
        select(Decision, Flag, Dataset, Study)
        .join(Flag,    Decision.flag_id    == Flag.id)
        .join(Dataset, Flag.dataset_id     == Dataset.id)
        .join(Study,   Dataset.study_id    == Study.id)
        .where(Study.id == study_id)
        .order_by(Decision.decided_at)
    ).all()

    records = _build_records(rows)
    content_hash = _hash_records(records)
    export_ref = str(uuid.uuid4())
    exported_at = datetime.now(timezone.utc)

    metadata = {
        "export_ref":     export_ref,
        "study_id":       study_id,
        "study_name":     study.name,
        "sponsor_id":     study.sponsor_id,
        "study_type":     study.study_type,
        "species":        study.species,
        "exported_by":    exported_by,
        "exported_at":    exported_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "record_count":   len(records),
        "system_version": SYSTEM_VERSION,
        "reason":         reason,
        "content_hash":   content_hash,
    }

    payload = {"export_metadata": metadata, "records": records}

    audit_export = AuditExport(
        study_id=study_id,
        export_ref=export_ref,
        exported_by=exported_by,
        exported_at=exported_at.replace(tzinfo=None),  # SQLite stores as naive
        record_count=len(records),
        content_hash=content_hash,
        export_format=export_format,
        system_version=SYSTEM_VERSION,
        reason=reason,
    )
    db.add(audit_export)
    db.commit()
    db.refresh(audit_export)

    return audit_export, payload


def list_exports(db: Session, study_id: int) -> List[AuditExport]:
    return list(
        db.execute(
            select(AuditExport)
            .where(AuditExport.study_id == study_id)
            .order_by(AuditExport.exported_at.desc())
        )
        .scalars()
        .all()
    )


def get_export_by_ref(db: Session, export_ref: str) -> Optional[AuditExport]:
    return db.execute(
        select(AuditExport).where(AuditExport.export_ref == export_ref)
    ).scalars().first()
