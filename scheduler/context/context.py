import logging
from dataclasses import dataclass

from scheduler.config import settings


@dataclass
class AppContext:
    config: settings.Settings = settings.Settings()
