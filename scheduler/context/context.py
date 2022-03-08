import json
import logging.config
from types import SimpleNamespace
from typing import Dict

import scheduler
from scheduler.config import settings
from scheduler.connectors import services


class AppContext:
    """AppContext allows shared data between modules"""

    config: settings.Settings
    services: Dict[str, services.HTTPService]

    def __init__(self):
        self.config = settings.Settings()

        # Load logging configuration
        with open(self.config.log_cfg, "rt") as f:
            logging.config.dictConfig(json.load(f))

        # Register external services, SimpleNamespace allows us to use dot
        # notation
        self.services = SimpleNamespace(
            **{
                services.Katalogus.name: services.Katalogus(
                    host=self.config.host_katalogus,
                    source=f"scheduler/{scheduler.__version__}",
                ),
                services.Bytes.name: services.Bytes(
                    host=self.config.host_bytes,
                    user=self.config.host_bytes_user,
                    password=self.config.host_bytes_password,
                    source=f"scheduler/{scheduler.__version__}",
                ),
                services.Octopoes.name: services.Octopoes(
                    host=self.config.host_octopoes,
                    source=f"scheduler/{scheduler.__version__}",
                ),
                services.Rocky.name: services.Rocky(
                    host=self.config.host_rocky,
                    source=f"scheduler/{scheduler.__version__}",
                ),
                services.XTDB.name: services.XTDB(
                    host=self.config.host_xtdb,
                    source=f"scheduler/{scheduler.__version__}",
                ),
            }
        )
