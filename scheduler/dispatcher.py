import logging
import time
import uuid
from typing import Any

import celery
import pydantic

from scheduler import context, queue


class Dispatcher:
    """Dispatcher allows to continuously pop items off a priority queue and
    dispatches items to be handled. By what, and who this is being handled is
    done by a sub-classing the dispatcher and implementing the `dispatch()`
    method.
    """

    logger: logging.Logger
    pq: queue.PriorityQueue
    item_type: pydantic.BaseModel
    task: pydantic.BaseModel

    def __init__(self, pq: queue.PriorityQueue, item_type: pydantic.BaseModel):
        self.logger = logging.getLogger(__name__)
        self.pq = pq
        self.threshold = float("inf")
        self.item_type = item_type

    def _can_dispatch(self):
        # Every item lower than the threshold is dispatched immediately
        peek_item = self.pq.peek(0)[1]
        if float(peek_item.priority) <= self.get_threshold():
            return True

        return False

    def _is_valid_item(self, item: Any) -> bool:
        return isinstance(item, self.item_type)

    def get_threshold(self) -> float:
        return self.threshold

    def dispatch(self) -> None:
        if not self._can_dispatch():
            self.logger.debug("Nothing to dispatch")
            return

        p_item = self.pq.pop()

        self.logger.info(f"Dispatching task {p_item.item}")

        if not self._is_valid_item(p_item.item):
            raise ValueError(f"Item must be of type {self.item_type.__name__}")

        self.task = p_item.item

    def run(self):
        while True:
            if self.pq.empty():
                self.logger.debug("Queue is empty, sleeping ...")
                time.sleep(10)
                continue

            self.dispatch()


class CeleryDispatcher(Dispatcher):
    queue: str
    task_name: str
    ctx: context.AppContext

    def __init__(
        self,
        ctx: context.AppContext,
        pq: queue.PriorityQueue,
        item_type: pydantic.BaseModel,
        queue: str,
        task_name: str,
    ):
        super().__init__(pq=pq, item_type=item_type)

        self.ctx = ctx
        self.queue = queue
        self.task_name = task_name

        self.app = celery.Celery(
            name="",  # FIXME
            broker=self.ctx.config.dsp_broker_url,
        )

        self.app.conf.update(
            task_serializer="json",
            result_serializer="json",
            event_serializer="json",
            accept_content=["application/json", "application/x-python-serialize"],
            result_accept_content=["application/json", "application/x-python-serialize"],
        )

    def dispatch(self) -> None:
        super().dispatch()

        self.app.send_task(
            name=self.task_name,
            args=(self.task.dict(),),
            queue=self.queue,
            task_id=self.task.id,
        )


class BoefjeDispatcher(CeleryDispatcher):
    pass


class BoefjeDispatcherTimebased(CeleryDispatcher):
    """A time-based BoefjeDispatcher allows for executing jobs at a certain
    time. The threshold of dispatching jobs is the current time, and based
    on the time-based priority score of the jobs on the queue. The dispatcher
    determines to dispatch the job.
    """

    def get_threshold(self) -> float:
        return time.time()
