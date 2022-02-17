import logging
from typing import List

import fastapi
import scheduler
import uvicorn
from scheduler import context, datastore, models, queue


class Server:
    """Server that exposes API endpoints for the scheduler."""

    logger: logging.Logger
    ctx: context.AppContext
    api: fastapi.FastAPI
    queues: List[queue.PriorityQueue]

    def __init__(self, ctx: context.AppContext, queues: List[queue.PriorityQueue]):
        self.logger = logging.getLogger(__name__)
        self.ctx = ctx
        self.api = fastapi.FastAPI()

        self.queues = {q.name: q for q in queues}

        self.api.add_api_route(
            path="/",
            endpoint=self.root,
            methods=["GET"],
        )
        self.api.add_api_route(
            path="/health",
            endpoint=self.health,
            methods=["GET"],
            response_model=models.ServiceHealth,
        )
        self.api.add_api_route(
            path="/queue/{queue_name}/pop",
            endpoint=self.queue_pop,
            methods=["GET"],
            # response_model=models.QueueItem,
        )

    async def root(self):
        return {"message": "hello, world"}

    async def health(self) -> models.ServiceHealth:
        return models.ServiceHealth(service="scheduler", healthy=True, version=scheduler.__version__)

    async def queue_pop(self, queue_name: str):
        return self.queues[queue_name].pop().item.json()

    def run(self):
        uvicorn.run(self.api, host="0.0.0.0", log_config=None)  # FIXME: make host configurable
