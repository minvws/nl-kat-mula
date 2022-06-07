import json
import logging.config
import threading
from types import SimpleNamespace

import scheduler
from scheduler.config import settings
from scheduler.connectors import listeners, services


class AppContext:
    """AppContext allows shared data between modules.

    Attributes:
        config:
            A settings.Settings object containing configurable application
            settings
        services:
            A dict containing all the external services connectors that
            are used and need to be shared in the scheduler application.
        stop_event: A threading.Event object used for communicating a stop
            event across threads.
    """

    def __init__(self) -> None:
        """Initializer of the AppContext class."""
        self.config: settings.Settings = settings.Settings()

        # Load logging configuration
        with open(self.config.log_cfg, "rt", encoding="utf-8") as f:
            logging.config.dictConfig(json.load(f))

        # Register external services, SimpleNamespace allows us to use dot
        # notation
        self.services = SimpleNamespace(
            **{
                services.Octopoes.name: services.Octopoes(
                    host=self.config.host_octopoes,
                    source=f"scheduler/{scheduler.__version__}",
                ),
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
                listeners.ScanProfile.name: listeners.ScanProfile(
                    dsn=self.config.host_scan_profile,
                ),
                listeners.RawData.name: listeners.RawData(
                    dsn=self.config.host_raw_data,
                ),
            }
        )

        self.stop_event: threading.Event = threading.Event()
