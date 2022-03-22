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
    done by a sub-classing and extending the dispatcher and implementing the
    `dispatch()` method.

    Attributes:
        logger:
            The logger for the class.
        pq:
            A queue.PriorityQueue instance.
        threshold:
            A float describing the threshold that needs to be adhered too
            for dispatching tasks from the priority queue. By default this is
            set to `float("inf")` meaning all the items on the queue are
            allowed to be dispatched. Set this threshold by implementing
            the `get_threshold` method.
        item_type:
            A pydantic.BaseModel object that specifies the type of item that
            should be dispatched, this helps with validation.
        task:
            A pydantic.BaseModel object that defines the task that is going
            to be dispatched. Used for sub classes of the dispatcher to
            reference the task that should be dispatched.
    """

    def __init__(self, pq: queue.PriorityQueue, item_type: pydantic.BaseModel):
        """Initialize the Dispatcher class

        Args:
            pq:
                A queue.PriorityQueue instance.
            item_type:
                A pydantic.BaseModel object that specifies the type of item
                that should be dispatched, this helps with validation.
        """
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.pq: queue.PriorityQueue = pq
        self.threshold: float = float("inf")
        self.item_type: pydantic.BaseModel = item_type
        self.task: pydantic.BaseModel = None

    def _can_dispatch(self) -> bool:
        """Checks the first item of the priority queue, whether or not items
        priority higher in priority and thus lower or equal to the defined
        threshold should be dispatched.

        Returns:
            A boolean representing whether the item with the highest priority
            on the queue, should be dispatched.
        """
        # TODO: since we have a dependency on the PriorityQueue and how items
        # are defined on the queue, we should make that more explicity so
        # that we don't heave to use indexing here to get the task item from
        # an entry
        peek_item = self.pq.peek(0)[1]
        if float(peek_item.priority) <= self.get_threshold():
            return True

        return False

    def _is_valid_item(self, item: Any) -> bool:
        """Check if an item is of the same type as the defined item_type

        Args:
            item: typing.Any

        Returns:
            A boolean
        """
        return isinstance(item, self.item_type)

    def get_threshold(self) -> float:
        """Return the threshold of that needs to be adhered to.

        Returns:
            A float returning the threshold attribute.
        """
        return self.threshold

    def dispatch(self) -> None:
        """Pop and dispatch a task item from a priority queue entry. This
        method should be extended by subclasses to implement its specific
        dispatching strategy.

        Returns:
            None
        """
        if not self._can_dispatch():
            self.logger.debug("Nothing to dispatch")
            return

        p_item = self.pq.pop()

        self.logger.info(f"Dispatching task {p_item.item}")

        if not self._is_valid_item(p_item.item):
            raise ValueError(f"Item must be of type {self.item_type.__name__}")

        self.task = p_item.item

    def run(self) -> None:
        """Continuously dispatch items from the priority queue."""
        while True:
            if self.pq.empty():
                self.logger.debug("Queue is empty, sleeping ...")
                time.sleep(10)
                continue

            self.dispatch()

            time.sleep(0.01)


class CeleryDispatcher(Dispatcher):
    """A Celery implementation of a Dispatcher.

    Attributes:
        ctx:
            A context.AppContext instance.
        queue:
            A string descibing the Celery queue to which the tasks need to
            be dispatched.
        task_name:
            A string describing the name of the Celery task
    """

    def __init__(
        self,
        ctx: context.AppContext,
        pq: queue.PriorityQueue,
        item_type: pydantic.BaseModel,
        queue: str,
        task_name: str,
    ):
        """Initialize the CeleryDispatcher class.

        Args:
            ctx:
                A contex.AppContext instance.
            pq:
                A queue.PriorityQueue instance.
            item_type:
                A pydantic.BaseModel object that specifies the type of item
                that should be dispatched, this helps with validation.
            queue:
                A string descibing the Celery queue to which the tasks need to
                be dispatched.
            task_name:
                A string describing the name of the Celery task
        """
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
