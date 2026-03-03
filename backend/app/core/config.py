from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "Decision Tracker"
    debug: bool = True
    database_url: str = "sqlite:///./data/decisiontracker.db"
    api_v1_prefix: str = "/api/v1"
    anthropic_api_key: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()
