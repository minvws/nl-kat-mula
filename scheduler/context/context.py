import json
import logging.config
from types import SimpleNamespace
from typing import Dict

from scheduler.config import settings
from scheduler.connector import service


class AppContext:
    """AppContext allows shared data between modules"""

    config: settings.Settings
    services: Dict[str, service.Service]

    def __init__(self):
        self.config = settings.Settings()

        # Load logging configuration
        with open(self.config.log_cfg, "rt") as f:
            logging.config.dictConfig(json.load(f))

        # Register external services
        self.services = SimpleNamespace(
            **{
                service.Katalogus.name: service.Katalogus(self.config.katalogus_api),
            }
        )
