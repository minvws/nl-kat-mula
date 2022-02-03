import os
from pathlib import Path

from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    debug: bool = False
    log_cfg: str = os.path.join(Path(__file__).parent.parent.parent, "logging.json")
    db_dsn: str = "postgresql://postgres:postgres@scheduler-db:5432/scheduler"
    api_host: str = "0.0.0.0"
    api_port: int = 8004

    class Config:
        env_prefix = "SCHEDULER_"
