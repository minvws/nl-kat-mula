import json
import logging.config

from scheduler.config import settings


class AppContext:
    config: settings.Settings

    def __init__(self):
        self.config = settings.Settings()

        with open(self.config.logging_cfg, "rt") as f:
            logging.config.dictConfig(json.load(f))
