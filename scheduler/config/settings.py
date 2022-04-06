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
    api_port: int = Field(8000, env="SCHEDULER_API_PORT")

    # External services settings
    host_katalogus: str = Field(..., env="KATALOGUS_API")
    host_bytes: str = Field(..., env="BYTES_API")
    host_octopoes: str = Field(..., env="OCTOPOES_API")
    # host_rocky: str = Field(..., env="ROCKY_API")

    host_bytes_user: str = Field(..., env="BYTES_USERNAME")
    host_bytes_password: str = Field(..., env="BYTES_PASSWORD")

    # Listener settings
    # lst_octopoes: str = Field(..., env="QUEUE_URI")

    # Queue settings (0 is infinite)
    pq_maxsize: int = Field(0, env="SHEDULER_PQ_MAXSIZE")
    pq_populate_interval: int = Field(60, env="SHEDULER_PQ_INTERVAL")

    # Dispatcher settings
    dsp_broker_url: str = Field(..., env="SCHEDULER_DSP_BROKER_URL")

    # class Config:
    #     env_prefix = "SCHEDULER_"
