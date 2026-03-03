from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.dataset import Dataset
    from app.models.decision import Decision


class Flag(Base):
    __tablename__ = "flags"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    column_name: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_value: Mapped[str] = mapped_column(String(500), nullable=False)
    proposed_value: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    flag_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # low | medium | high
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    biological_reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    # pending | confirmed | rejected | overridden
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    dataset: Mapped[Dataset] = relationship("Dataset", back_populates="flags")
    decisions: Mapped[list[Decision]] = relationship("Decision", back_populates="flag", cascade="all, delete-orphan")
