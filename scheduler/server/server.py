import logging
import queue as _queue
from typing import Any, Dict, List

import fastapi
import scheduler
import uvicorn
from scheduler import context, models, queues


# TODO: decide if we need AppContext here, since we're only using host and
# api
class Server:
    """Server that exposes API endpoints for the scheduler."""

    def __init__(self, ctx: context.AppContext, priority_queues: Dict[str, queues.PriorityQueue]):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.ctx: context.AppContext = ctx
        self.queues: Dict[str, queues.PriorityQueue] = priority_queues

        self.api = fastapi.FastAPI()

        self.api.add_api_route(
            path="/",
            endpoint=self.root,
            methods=["GET"],
            status_code=200,
        )

        self.api.add_api_route(
            path="/health",
            endpoint=self.health,
            methods=["GET"],
            response_model=models.ServiceHealth,
            status_code=200,
        )

        self.api.add_api_route(
            path="/queues",
            endpoint=self.get_queues,
            methods=["GET"],
            response_model=List[models.Queue],
            status_code=200,
        )

        self.api.add_api_route(
            path="/queues/{queue_id}",
            endpoint=self.get_queue,
            methods=["GET"],
            response_model=models.Queue,
            status_code=200,
        )

        self.api.add_api_route(
            path="/queues/{queue_id}/pop",
            endpoint=self.pop_queue,
            methods=["GET"],
            response_model=models.QueuePrioritizedItem,
            status_code=200,
        )

        self.api.add_api_route(
            path="/queues/{queue_id}/push",
            endpoint=self.push_queue,
            methods=["POST"],
        )

    async def root(self) -> Any:
        return {"message": "hello, world"}

    async def health(self) -> Any:
        response = models.ServiceHealth(
            service="scheduler",
            healthy=True,
            version=scheduler.__version__,
        )

        for service in self.ctx.services.__dict__.values():
            response.externals[service.name] = service.is_healthy()

        return response

    async def get_queues(self) -> Any:
        return [models.Queue(**q.dict()) for q in self.queues.values()]

    async def get_queue(self, queue_id: str) -> Any:
        q = self.queues.get(queue_id)
        if q is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="queue not found",
            )

        return models.Queue(**q.dict())

    async def pop_queue(self, queue_id: str) -> Any:
        q = self.queues.get(queue_id)
        if q is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="queue not found",
            )

        try:
            item = q.pop()
            return models.QueuePrioritizedItem(**item.dict())
        except _queue.Empty as exc_empty:
            raise fastapi.HTTPException(
                status_code=400,
                detail="queue is empty",
            ) from exc_empty

    async def push_queue(self, queue_id: str, item: models.QueuePrioritizedItem) -> Any:
        q = self.queues.get(queue_id)
        if q is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="queue not found",
            )

        try:
            q.push(queues.PrioritizedItem(**item.dict()))
        except _queue.Full as exc_full:
            raise fastapi.HTTPException(
                status_code=400,
                detail="queue is full",
            ) from exc_full
        except ValueError as exc_value:
            raise fastapi.HTTPException(
                status_code=400,
                detail="invalid item",
            ) from exc_value

        return fastapi.Response(status_code=204)

    def run(self) -> None:
        uvicorn.run(
            self.api,
            host=self.ctx.config.api_host,
            port=self.ctx.config.api_port,
            log_config=None,
        )
