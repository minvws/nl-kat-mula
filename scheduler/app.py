import datetime
import logging
import os
import threading
import time
import uuid
from datetime import timedelta
from typing import Any, Callable, Dict, List

import requests

from scheduler import context, dispatchers, queues, rankers, schedulers, server
from scheduler.connectors import listeners
from scheduler.models import OOI, BoefjeTask, Organisation
from scheduler.utils import thread


class App:
    """Main application definition for the scheduler implementation of KAT.

    Attributes:
        logger:
            The logger for the class.
        ctx:
            Application context of shared data (e.g. configuration, external
            services connections).
        listeners:
            A dict of connector.Listener instances.
        queues:
            A dict of queue.PriorityQueue instances.
        server:
            A server.Server instance.
        threads:
            A dict of ThreadRunner instances, used for runner processes
            concurrently.
        stop_event: A threading.Event object used for communicating a stop
            event across threads.
    """

    def __init__(self, ctx: context.AppContext) -> None:
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.ctx: context.AppContext = ctx
        self.threads: Dict[str, thread.ThreadRunner] = {}
        self.stop_event: threading.Event = self.ctx.stop_event

        self.schedulers: Dict[str, schedulers.Scheduler] = {}
        self.initialize_boefje_schedulers()

        # FIXME: with scheduler or app?
        # Initialize event stream listeners
        self.listeners: Dict[str, listeners.Listener] = {}

        # Initialize API server
        self.server: server.Server = server.Server(
            ctx=self.ctx,
            priority_queues={k: s.queue for k, s in self.schedulers.items()},
        )

    def shutdown(self) -> None:
        """Gracefully shutdown the scheduler, and all threads."""
        self.logger.warning("Shutting down...")

        for scheduler in self.schedulers.values():
            for thread in scheduler.threads.values():
                thread.join(5)

        for thread in self.threads.values():
            thread.join(5)

        self.logger.warning("Shutdown complete")

        os._exit(0)

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
        self.threads[name] = thread.ThreadRunner(
            target=func,
            stop_event=self.stop_event,
            interval=interval,
        )
        self.threads[name].setDaemon(daemon)
        self.threads[name].start()

    def initialize_boefje_schedulers(self) -> None:
        orgs = self.ctx.services.katalogus.get_organisations()
        for org in orgs:
            queue = queues.BoefjePriorityQueue(
                pq_id=org.id,
                maxsize=self.ctx.config.pq_maxsize,
                item_type=BoefjeTask,
                allow_priority_updates=True,
            )

            dispatcher = dispatchers.BoefjeDispatcher(
                ctx=self.ctx,
                pq=queue,
                item_type=BoefjeTask,
                celery_queue="boefjes",
                task_name="tasks.handle_boefje",
            )

            ranker = rankers.BoefjeRanker(
                ctx=self.ctx,
            )

            scheduler = schedulers.BoefjeScheduler(
                ctx=self.ctx,
                scheduler_id=org.id,
                queue=queue,
                dispatcher=dispatcher,
                ranker=ranker,
                organisation=org,
            )

            self.schedulers[org.id] = scheduler

    def run(self) -> None:
        """Start the main scheduler application, and run in threads the
        following processes:

            * api server
            * listeners
            * queue populators
            * dispatchers
        """
        # API Server
        self._run_in_thread(name="server", func=self.server.run, daemon=False)

        # Listeners for OOI changes
        for k, l in self.listeners.items():
            self._run_in_thread(name=k, func=l.listen)

        # Start the schedulers
        for k, s in self.schedulers.items():
            s.run()

        # Main thread
        while not self.stop_event.is_set():
            time.sleep(0.01)

        self.shutdown()
