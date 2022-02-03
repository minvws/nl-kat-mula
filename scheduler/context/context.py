import json
import logging.config

from scheduler.config import settings


class AppContext:
    """AppContext allows shared data between modules"""

    config: settings.Settings

    def __init__(self):
        self.config = settings.Settings()

        with open(self.config.log_cfg, "rt") as f:
            logging.config.dictConfig(json.load(f))
