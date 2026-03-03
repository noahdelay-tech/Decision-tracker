import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Prefer the full pydantic-based settings when available (Docker / full env).
# Fall back to a plain env-var / default so lightweight scripts (seed.py,
# migrations) work locally without pydantic_settings installed.
try:
    from app.core.config import settings
    _DATABASE_URL = settings.database_url
except ImportError:
    _DATABASE_URL = os.getenv(
        "DATABASE_URL", "sqlite:///./data/decisiontracker.db"
    )

engine = create_engine(
    _DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
