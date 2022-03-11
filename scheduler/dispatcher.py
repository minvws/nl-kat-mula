import logging
import time
import uuid

import celery

from scheduler import context, queue


class Dispatcher:
    """Dispatcher allows to continuously pop items off a priority queue and
    dispatches items to be handled. By what, and who this is being handled is
    done by a sub-classing the dispatcher and implementing the `dispatch()`
    method.
    """

    logger: logging.Logger
    pq: queue.PriorityQueue

    def __init__(self, pq: queue.PriorityQueue):
        self.logger = logging.getLogger(__name__)
        self.pq = pq
        self.threshold = float("inf")

    def run(self):
        while True:
            if self.pq.empty():
                self.logger.debug("Queue is empty, sleeping ...")
                time.sleep(10)
                continue

            self.can_dispatch()

    def can_dispatch(self):
        # Every item lower than the threshold is dispatched immediately
        peek_item = self.pq.peek(0)[1]
        if float(peek_item.priority) <= self.get_threshold():
            item = self.pq.pop()
            self.dispatch(item)

    def get_threshold(self) -> float:
        return self.threshold

    def dispatch(self, item: queue.PrioritizedItem):
        self.logger.info(f"Dispatching task {item}")


class CeleryDispatcher(Dispatcher):
    queue: str
    task_name: str
    ctx: context.AppContext

    def __init__(
        self,
        ctx: context.AppContext,
        pq: queue.PriorityQueue,
        queue: str,
        task_name: str,
    ):
        super().__init__(pq=pq)

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

    def dispatch(self, item: queue.PrioritizedItem):
        super().dispatch(item)

        task = item.item

        self.app.send_task(
            name=self.task_name,
            args=(task.dict(),),
            queue=self.queue,
            task_id=task.id,
        )


class BoefjeDispatcher(CeleryDispatcher):
    def get_threshold(self) -> float:
        return time.time()
