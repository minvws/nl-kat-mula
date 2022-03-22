import logging
from typing import Dict, List, Optional

import _queue
import fastapi
import scheduler
import uvicorn
from fastapi.responses import JSONResponse
from scheduler import context, datastore, models, queue


# TODO: decide if we need AppContext here, since we're only using host and
# api
class Server:
    """Server that exposes API endpoints for the scheduler."""

    def __init__(self, ctx: context.AppContext, queues: Dict[str, queue.PriorityQueue]):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.ctx: context.AppContext = ctx
        self.queues: Dict[str, queue.PriorityQueue] = queues

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
            response_model=List[models.Queue],
        )

        self.api.add_api_route(
            path="/queues/{queue_id}",
            endpoint=self.get_queue,
            methods=["GET"],
            response_model=models.Queue,
        )

        self.api.add_api_route(
            path="/queues/{queue_id}/pop",
            endpoint=self.pop_queue,
            methods=["GET"],
            response_model=models.QueueItem,
        )

        self.api.add_api_route(
            path="/queues/{queue_id}/push",
            endpoint=self.push_queue,
            methods=["POST"],
        )

    async def root(self) -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content={"message": "hello, world"},
        )

    async def health(self) -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content=models.ServiceHealth(
                service="scheduler",
                healthy=True,
                version=scheduler.__version__,
            ),
        )

    async def get_queues(self) -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content=[models.Queue(**q.dict()) for q in self.queues.values()],
        )

    async def get_queue(self, queue_id: str) -> JSONResponse:
        q = self.queues.get(queue_id)
        if q is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="queue not found",
            )

        return JSONResponse(
            status_code=200,
            content=models.Queue(**q.dict()),
        )

    async def pop_queue(self, queue_id: str) -> JSONResponse:
        q = self.queues.get(queue_id)
        if q is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="queue not found",
            )

        try:
            item = q.pop()
            return JSONResponse(
                status_code=200,
                content=models.QueueItem(**item.dict()),
            )
        except _queue.Empty:
            raise fastapi.HTTPException(
                status_code=400,
                detail="queue is empty",
            )

    async def push_queue(self, queue_id: str, item: models.QueueItem) -> JSONResponse:
        q = self.queues.get(queue_id)
        if q is None:
            raise fastapi.HTTPException(
                status_code=404,
                detail="queue not found",
            )

        try:
            q.push(queue.PrioritizedItem(**item.dict()))
        except _queue.Full:
            raise fastapi.HTTPException(
                status_code=400,
                detail="queue is full",
            )
        except ValueError:
            raise fastapi.HTTPException(
                status_code=400,
                detail="invalid item",
            )

        return JSONResponse(status_code=204)

    def run(self) -> None:
        uvicorn.run(
            self.api,
            host=self.ctx.config.api_host,
            port=self.ctx.config.api_port,
            log_config=None,
        )
