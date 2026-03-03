from fastapi import APIRouter

from app.api.v1.endpoints import audit, briefings, datasets, flags, ingest, patterns, studies

api_router = APIRouter()
api_router.include_router(ingest.router)
api_router.include_router(datasets.router)
api_router.include_router(flags.router)
api_router.include_router(patterns.router)
# studies registered before briefings: both share prefix="/studies"; exact study
# routes (/studies/, /studies/{id}) need to resolve before briefing sub-paths.
api_router.include_router(studies.router)
api_router.include_router(briefings.router)
api_router.include_router(audit.router)
