"""
pattern.py

Stores aggregated decision patterns keyed by
  sponsor_id × flag_type × column_name

Only `confirmed` and `overridden` decisions contribute.
Rebuilt on demand via POST /api/v1/patterns/rebuild.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Pattern(Base):
    __tablename__ = "patterns"

    __table_args__ = (
        UniqueConstraint("sponsor_id", "flag_type", "column_name", name="uq_pattern_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Grouping key
    sponsor_id:  Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    flag_type:   Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    column_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Aggregated statistics
    occurrence_count:   Mapped[int]   = mapped_column(Integer, nullable=False, default=0)
    confirmation_rate:  Mapped[float] = mapped_column(Float,   nullable=False, default=0.0)

    # Most common corrected value when action == "overridden" (nullable)
    common_override: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Up to 3 sample biological_reasoning strings from source flags
    example_reasonings: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    last_updated: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
