import os
from pathlib import Path

from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    debug: bool = False
    logging_cfg: str = os.path.join(Path(__file__).parent.parent.parent, "logging.json")
    scheduler_db_url: str = "postgresql://postgres:postgres@scheduler-db:5432/scheduler"
