"""
audit_export.py

Immutable audit export records for 21 CFR Part 11 compliance.
Each row represents one signed, timestamped export snapshot.
The content_hash (SHA-256) covers the full serialised export payload,
providing tamper-evidence without requiring a PKI infrastructure.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.study import Study


class AuditExport(Base):
    __tablename__ = "audit_exports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    study_id: Mapped[int] = mapped_column(
        ForeignKey("studies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Stable, shareable reference (UUID4 as string)
    export_ref: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)

    exported_by: Mapped[str] = mapped_column(String(100), nullable=False)
    exported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # How many decision records are in this export
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # SHA-256 hex digest of the canonical JSON payload
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # "json" or "csv"
    export_format: Mapped[str] = mapped_column(String(10), nullable=False, default="json")

    # Software name + version stamped at export time
    system_version: Mapped[str] = mapped_column(String(100), nullable=False, default="decision-tracker/1.0")

    # Reason for export (optional free text, supports audit inquiries)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="routine_audit")

    study: Mapped[Study] = relationship("Study")
