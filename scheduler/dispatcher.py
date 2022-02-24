import logging
import time
import uuid

import celery

from scheduler import context, queue


class Dispatcher:
    logger: logging.Logger
    ctx: context.AppContext
    pq: queue.PriorityQueue

    def __init__(self, ctx: context.AppContext, pq: queue.PriorityQueue):
        self.logger = logging.getLogger(__name__)
        self.ctx = ctx
        self.pq = pq

    def run(self):
        while True:
            if self.pq.empty():
                self.logger.info("Queue is empty, sleeping ...")
                time.sleep(10)
                continue

            item = self.pq.pop()
            self.dispatch(item)

    def dispatch(self, item: queue.PrioritizedItem):
        self.logger.info(f"Dispatching task {item}")


class CeleryDispatcher(Dispatcher):
    def __init__(self, ctx: context.AppContext, pq: queue.PriorityQueue, queue: str):
        super().__init__(ctx=ctx, pq=pq)
        self.queue = queue

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
            name="tasks.handle_boefje",  # FIXME: from config, is defined
            args=(task.dict(),),
            queue=self.queue,
            task_id=task.id,
        )
