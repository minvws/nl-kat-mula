import logging
from typing import Dict, List, Optional

import _queue
import fastapi
import scheduler
import uvicorn
from scheduler import context, datastore, models, queue


# TODO: decide if we need AppContext here, since we're only using host and
# api
class Server:
    """Server that exposes API endpoints for the scheduler."""

    logger: logging.Logger
    ctx: context.AppContext
    api: fastapi.FastAPI
    queues: Dict[str, queue.PriorityQueue]

    def __init__(self, ctx: context.AppContext, queues: Dict[str, queue.PriorityQueue]):
        self.logger = logging.getLogger(__name__)
        self.ctx = ctx
        self.queues = queues

        self.api = fastapi.FastAPI()

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
            path="/queues",
            endpoint=self.get_queues,
            methods=["GET"],
            # response_model=models.QueueItem,
        )

        self.api.add_api_route(
            path="/queues/{queue_id}",
            endpoint=self.get_queue,
            methods=["GET"],
        )

        self.api.add_api_route(
            path="/queues/{queue_id}/pop",
            endpoint=self.pop_queue,
            methods=["GET"],
            # response_model=models.QueueItem,
        )

        self.api.add_api_route(
            path="/queues/{queue_id}/push",
            endpoint=self.push_queue,
            methods=["POST"],
            status_code=204,
            # response_model=models.QueueItem,
        )

    async def root(self):
        return {"message": "hello, world"}

    async def health(self) -> models.ServiceHealth:
        return models.ServiceHealth(service="scheduler", healthy=True, version=scheduler.__version__)

    async def get_queues(self):
        return [q.json() for q in self.queues.values()]

    # TODO: return model
    async def get_queue(self, queue_id: str):
        q = self.queues.get(queue_id)
        if q is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="queue not found",
            )

        return self.queues.get(queue_id).json()

    # TODO: return model
    async def pop_queue(self, queue_id: str):
        q = self.queues.get(queue_id)
        if q is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="queue not found",
            )

        try:
            return q.pop().json()
        except _queue.Empty:
            return {}

    # TODO: full
    # TODO: return model
    async def push_queue(self, queue_id: str):
        # self.queues[queue_id].push()
        q = self.queues.get(queue_id)
        if q is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="queue not found",
            )

        pass

    def run(self):
        uvicorn.run(
            self.api,
            host=self.ctx.config.api_host,
            port=self.ctx.config.api_port,
            log_config=None,
        )
