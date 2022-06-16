import logging
import queue as _queue
from typing import Any, Dict, List, Union

import fastapi
import scheduler
import uvicorn
from scheduler import context, models, queues, schedulers


class Server:
    """Server that exposes API endpoints for the scheduler."""

    def __init__(
        self,
        ctx: context.AppContext,
        schedulers: Dict[str, Union[schedulers.BoefjeScheduler, schedulers.NormalizerScheduler]],
    ):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.ctx: context.AppContext = ctx
        self.schedulers = schedulers
        self.queues: Dict[str, queues.PriorityQueue] = {k: s.queue for k, s in self.schedulers.items()}

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
            path="/schedulers",
            endpoint=self.get_schedulers,
            methods=["GET"],
            response_model=List[models.Scheduler],
            status_code=200,
        )

        self.api.add_api_route(
            path="/schedulers/{scheduler_id}",
            endpoint=self.get_scheduler,
            methods=["GET"],
            response_model=models.Scheduler,
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
        return None

    async def health(self) -> Any:
        return models.ServiceHealth(
            service="scheduler",
            healthy=True,
            version=scheduler.__version__,
        )

    async def get_schedulers(self) -> Any:
        return [models.Scheduler(**s.dict()) for s in self.schedulers.values()]

    async def get_scheduler(self, scheduler_id: str) -> Any:
        s = self.schedulers.get(scheduler_id)
        if s is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="scheduler not found",
            )

        return models.Scheduler(**s.dict())

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
