import json
from logging import config
from pathlib import Path

from pydantic import BaseSettings

BASE_DIR = Path(__file__).parent.parent

with open(BASE_DIR / "logging.json", "r") as f:
    LOGGING_CONFIG = json.load(f)
    config.dictConfig(LOGGING_CONFIG)


class Settings(BaseSettings):
    queue_uri: str
    katalogus_api: str


settings = Settings()
