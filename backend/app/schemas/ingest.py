from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ColumnMappingEntry(BaseModel):
    """Per-column inference result returned in the ingest response."""
    original: str
    canonical: str
    normalized: str


class IngestResponse(BaseModel):
    dataset_id: int
    study_id: int
    filename: str
    row_count: int
    # original column name → canonical biological variable name
    column_mappings: Dict[str, str]
    # original column names that had no match in the lookup table
    unmapped_columns: List[str]


class DatasetSummary(BaseModel):
    """Lightweight metadata used by the dataset list endpoint."""
    id: int
    study_id: int
    filename: str
    upload_status: str
    row_count: Optional[int]
    column_count: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetDetailResponse(BaseModel):
    id: int
    study_id: int
    filename: str
    upload_status: str
    row_count: Optional[int]
    column_mappings: Optional[Dict[str, str]]
    unmapped_columns: Optional[List[str]]
    created_at: datetime
    # First ≤20 rows, keyed by original column name
    preview: List[Dict[str, Any]]

    model_config = {"from_attributes": True}
