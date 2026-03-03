from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BriefingRead(BaseModel):
    id: int
    study_id: int
    briefing_text: str
    model_used: str
    pattern_count: int
    generated_at: datetime

    model_config = {"from_attributes": True}


class BriefingGenerateRequest(BaseModel):
    force_regenerate: bool = False
