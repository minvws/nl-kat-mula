import json
import logging.config
from types import SimpleNamespace
from typing import Dict

import scheduler
from scheduler import connector
from scheduler.config import settings


class AppContext:
    """AppContext allows shared data between modules"""

    config: settings.Settings
    services: Dict[str, connector.service.HTTPService]

    def __init__(self):
        self.config = settings.Settings()

        # Load logging configuration
        with open(self.config.log_cfg, "rt") as f:
            logging.config.dictConfig(json.load(f))

        # Register external services, SimpleNamespace allows us to use dot
        # notation
        self.services = SimpleNamespace(
            **{
                connector.Katalogus.name: connector.Katalogus(
                    host=self.config.host_katalogus,
                    source=f"scheduler/{scheduler.__version__}",
                ),
                connector.Bytes.name: connector.Bytes(
                    host=self.config.host_bytes,
                    user=self.config.host_bytes_user,
                    password=self.config.host_bytes_password,
                    source=f"scheduler/{scheduler.__version__}",
                ),
                connector.Octopoes.name: connector.Octopoes(
                    host=self.config.host_octopoes,
                    source=f"scheduler/{scheduler.__version__}",
                ),
                connector.XTDB.name: connector.XTDB(
                    host=self.config.host_xtdb,
                    source=f"scheduler/{scheduler.__version__}",
                ),
            }
        )
