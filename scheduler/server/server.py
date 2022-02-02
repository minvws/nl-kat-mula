import logging

import fastapi
import uvicorn
from scheduler import db

from .router import router


class Server:
    """Server that exposes API endpoints for the scheduler."""

    logger: logging.Logger
    api: fastapi.FastAPI
    db: db.Database

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        self.api = fastapi.FastAPI()
        self.api.include_router(router)

    def run(self):
        uvicorn.run(self.api, host="0.0.0.0", log_config=None)  # FIXME: make host configurable
