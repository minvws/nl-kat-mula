import os
from pathlib import Path

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    debug: bool = Field(False, env="SCHEDULER_DEBUG")
    log_cfg: str = Field(
        os.path.join(Path(__file__).parent.parent.parent, "logging.json"),
        env="SCHEDULER_LOG_CFG",
    )

    # Server settings
    api_host: str = Field("0.0.0.0", env="SCHEDULER_API_HOST")
    api_port: int = Field(8004, env="SCHEDULER_API_PORT")

    # External services settings
    host_katalogus: str = Field(..., env="KATALOGUS_API")
    host_bytes: str = Field(..., env="BYTES_API")
    host_xtdb: str = Field(..., env="XTDB_URI")
    host_octopoes: str = Field(..., env="OCTOPOES_API")

    # Listener settings
    lst_octopoes: str = Field(..., env="QUEUE_URI")

    # Queue settings
    queue_maxsize: str = Field(100, env="QUEUE_SIZE")

    # class Config:
    #     env_prefix = "SCHEDULER_"
