"""
studies.py  –  /api/v1/studies/...

GET  /studies/           list all studies (with dataset counts)
POST /studies/           create a new study
GET  /studies/{id}       study detail with datasets and flag counts
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.dataset import Dataset
from app.models.flag import Flag
from app.models.study import Study

router = APIRouter(prefix="/studies", tags=["studies"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class StudyCreate(BaseModel):
    name: str
    sponsor_id: str
    study_type: str
    species: str


class StudySummary(BaseModel):
    id: int
    name: str
    sponsor_id: str
    study_type: str
    species: str
    dataset_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetInStudy(BaseModel):
    id: int
    filename: str
    upload_status: str
    row_count: Optional[int] = None
    flag_count: int = 0
    pending_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class StudyDetail(BaseModel):
    id: int
    name: str
    sponsor_id: str
    study_type: str
    species: str
    created_at: datetime
    datasets: List[DatasetInStudy]

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[StudySummary])
def list_studies(db: Session = Depends(get_db)):
    """List all studies ordered by creation date, newest first."""
    studies = (
        db.execute(select(Study).order_by(Study.created_at.desc()))
        .scalars()
        .all()
    )

    result: List[StudySummary] = []
    for s in studies:
        count = (
            db.execute(
                select(func.count(Dataset.id)).where(Dataset.study_id == s.id)
            ).scalar()
            or 0
        )
        result.append(
            StudySummary(
                id=s.id,
                name=s.name,
                sponsor_id=s.sponsor_id,
                study_type=s.study_type,
                species=s.species,
                dataset_count=count,
                created_at=s.created_at,
            )
        )
    return result


@router.post("/", response_model=StudySummary, status_code=201)
def create_study(body: StudyCreate, db: Session = Depends(get_db)):
    """Create a new study."""
    study = Study(
        name=body.name,
        sponsor_id=body.sponsor_id,
        study_type=body.study_type,
        species=body.species,
    )
    db.add(study)
    db.commit()
    db.refresh(study)
    return StudySummary(
        id=study.id,
        name=study.name,
        sponsor_id=study.sponsor_id,
        study_type=study.study_type,
        species=study.species,
        dataset_count=0,
        created_at=study.created_at,
    )


@router.get("/{study_id}", response_model=StudyDetail)
def get_study(study_id: int, db: Session = Depends(get_db)):
    """Get study detail including datasets with flag counts."""
    study = db.get(Study, study_id)
    if study is None:
        raise HTTPException(status_code=404, detail="Study not found")

    datasets = (
        db.execute(
            select(Dataset)
            .where(Dataset.study_id == study_id)
            .order_by(Dataset.created_at.desc())
        )
        .scalars()
        .all()
    )

    dataset_items: List[DatasetInStudy] = []
    for d in datasets:
        flag_count = (
            db.execute(
                select(func.count(Flag.id)).where(Flag.dataset_id == d.id)
            ).scalar()
            or 0
        )
        pending_count = (
            db.execute(
                select(func.count(Flag.id)).where(
                    Flag.dataset_id == d.id, Flag.status == "pending"
                )
            ).scalar()
            or 0
        )
        dataset_items.append(
            DatasetInStudy(
                id=d.id,
                filename=d.filename,
                upload_status=d.upload_status,
                row_count=d.row_count,
                flag_count=flag_count,
                pending_count=pending_count,
                created_at=d.created_at,
            )
        )

    return StudyDetail(
        id=study.id,
        name=study.name,
        sponsor_id=study.sponsor_id,
        study_type=study.study_type,
        species=study.species,
        created_at=study.created_at,
        datasets=dataset_items,
    )
