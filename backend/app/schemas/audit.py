from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AuditExportRead(BaseModel):
    id: int
    study_id: int
    export_ref: str
    exported_by: str
    exported_at: datetime
    record_count: int
    content_hash: str
    export_format: str
    system_version: str
    reason: str

    model_config = {"from_attributes": True}


class ExportRequest(BaseModel):
    exported_by: str
    reason: str = "routine_audit"
    export_format: str = "json"


class ExportResponse(BaseModel):
    export: AuditExportRead
    payload: Dict[str, Any]
