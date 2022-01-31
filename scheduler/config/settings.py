import os
from pathlib import Path

from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    debug: bool = False
    logging: str = os.path.join(Path(__file__).parent.parent.parent, "logging.json")
