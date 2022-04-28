import logging
import os
import threading
from typing import Any, Callable, Dict

from scheduler import context, dispatchers, queues, rankers, utils
from scheduler.utils import thread


class Scheduler:
    def __init__(
        self,
        ctx: context.AppContext,
        scheduler_id: str,
        queue: queues.PriorityQueue,
        ranker: rankers.Ranker,
        dispatcher: dispatchers.Dispatcher,
    ):
        self.ctx: context.AppContext = ctx
        self.scheduler_id = scheduler_id
        self.queue: queues.PriorityQueue = queue
        self.ranker: rankers.Ranker = ranker
        self.dispatcher: dispatchers.Dispatcher = dispatcher

        self.logger: logging.Logger = logging.getLogger(__name__)
        self.threads: Dict[str, thread.ThreadRunner] = {}
        self.stop_event: threading.Event = threading.Event()

    def populate_queue(self):
        raise NotImplementedError

    def _run_in_thread(
        self,
        name: str,
        func: Callable[[], Any],
        interval: float = 0.01,
        daemon: bool = False,
    ) -> None:
        """Make a function run in a thread, and add it to the dict of threads.

        Args:
            name: The name of the thread.
            func: The function to run in the thread.
            interval: The interval to run the function.
            daemon: Whether the thread should be a daemon.
        """
        self.threads[name] = utils.ThreadRunner(
            target=func,
            stop_event=self.stop_event,
            interval=interval,
        )
        self.threads[name].setDaemon(daemon)
        self.threads[name].start()

    def run(self) -> None:
        # Populator
        self._run_in_thread(
            name="populator",
            func=self.populate_queue,
            interval=self.ctx.config.pq_populate_interval,
        )

        # Dispatcher
        self._run_in_thread(
            name="dispatcher",  # FIXME
            func=self.dispatcher.run,
            daemon=False,
            interval=self.ctx.config.dsp_interval,
        )
