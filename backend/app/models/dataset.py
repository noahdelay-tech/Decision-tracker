from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.study import Study
    from app.models.flag import Flag


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    study_id: Mapped[int] = mapped_column(
        ForeignKey("studies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # pending | processing | complete | error
    upload_status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="pending")
    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Ingest-time schema inference results
    column_mappings: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON, nullable=True)
    unmapped_columns: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    # First 20 rows stored as list-of-dicts for the preview endpoint
    preview_rows: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    study: Mapped[Study] = relationship("Study", back_populates="datasets")
    flags: Mapped[List[Flag]] = relationship(
        "Flag", back_populates="dataset", cascade="all, delete-orphan"
    )
