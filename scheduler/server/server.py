import logging

import fastapi
import uvicorn
from scheduler import context, db

from .router import router


class Server:
    """Server that exposes API endpoints for the scheduler."""

    logger: logging.Logger
    api: fastapi.FastAPI
    db: db.Database
    ctx: context.AppContext

    def __init__(self, ctx: context.AppContext):
        self.logger = logging.getLogger(__name__)
        self.ctx = ctx
        self.api = fastapi.FastAPI()
        self.db = db.Database(dsn=self.ctx.config.db_dsn)

        self.api.include_router(router)

    def run(self):
        uvicorn.run(self.api, host="0.0.0.0", log_config=None)  # FIXME: make host configurable
