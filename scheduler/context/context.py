import json
import logging.config

from scheduler.config import settings


class AppContext:
    config: settings.Settings
    logger: logging.Logger = logging.getLogger(__name__)

    def __init__(self):
        self.config = settings.Settings()

        with open(self.config.logging, "rt") as f:
            logging.config.dictConfig(json.load(f))
