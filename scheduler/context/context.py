import json
import logging.config
from types import SimpleNamespace
from typing import Dict

import scheduler
from scheduler.config import settings
from scheduler.connector import service


class AppContext:
    """AppContext allows shared data between modules"""

    config: settings.Settings
    services: Dict[str, service.HTTPService]

    def __init__(self):
        self.config = settings.Settings()

        # Load logging configuration
        with open(self.config.log_cfg, "rt") as f:
            logging.config.dictConfig(json.load(f))

        # Register external services, SimpleNamespace allows us to use dot notation
        self.services = SimpleNamespace(
            **{
                service.Katalogus.name: service.Katalogus(
                    host=self.config.katalogus_api,
                    source=f"scheduler/{scheduler.__version__}",
                ),
                service.Bytes.name: service.Bytes(
                    host=self.config.bytes_api,
                    source=f"scheduler/{scheduler.__version__}",
                ),
                service.Octopoes.name: service.Octopoes(
                    host=self.config.octopoes_api,
                    source=f"scheduler/{scheduler.__version__}",
                ),
                service.XTDB.name: service.XTDB(
                    host=self.config.xtdb_uri,
                    source=f"scheduler/{scheduler.__version__}",
                ),
            }
        )
