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
from scheduler.models import OOI, BoefjeTask, NormalizerTask, Organisation
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
        """Initialize the application.

        Args:
            ctx:
                Application context of shared data (e.g. configuration,
                external services connections).
        """
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.ctx: context.AppContext = ctx
        self.threads: Dict[str, thread.ThreadRunner] = {}
        self.stop_event: threading.Event = self.ctx.stop_event

        # Initialize schedulers
        self.schedulers: Dict[str, schedulers.Scheduler] = {}
        self.initialize_boefje_schedulers()
        self.initialize_normalizer_schedulers()

        # Initialize listeners
        self.listeners: Dict[str, listeners.Listener] = {}

        # Initialize API server
        self.server: server.Server = server.Server(
            ctx=self.ctx,
            priority_queues={k: s.queue for k, s in self.schedulers.items()},
        )

    def shutdown(self) -> None:
        """Gracefully shutdown the scheduler, and all threads."""
        self.logger.warning("Shutting down...")

        for s in self.schedulers.values():
            s.stop()

        for t in self.threads.values():
            t.join(5)

        self.logger.warning("Shutdown complete")

        exit()

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
            daemon=daemon,
        )
        self.threads[name].start()

    def initialize_normalizer_schedulers(self) -> None:
        orgs = self.ctx.services.katalogus.get_organisations()
        for org in orgs:
            s = self.create_normalizer_scheduler(org)
            self.schedulers[s.scheduler_id] = s

    def create_normalizer_scheduler(self, org: Organisation) -> schedulers.NormalizerScheduler:
        """Create a normalizer scheduler for the given organisation."""
        queue = queues.NormalizerPriorityQueue(
            pq_id=org.id,
            maxsize=self.ctx.config.pq_maxsize,
            item_type=NormalizerTask,
            allow_priority_updates=True,  # TODO: check if this is correct
        )

        dispatcher = dispatchers.NormalizerDispatcher(
            ctx=self.ctx,
            pq=queue,
            item_type=NormalizerTask,
            celery_queue="normalizers",
            task_name="tasks.handle_normalizer", # TODO: check this in rbmq
        )

        ranker = rankers.NormalizerRanker(
            ctx=self.ctx,
        )

        scheduler = schedulers.NormalizerScheduler(
            ctx=self.ctx,
            scheduler_id=f"normalizer-{org.id}",
            queue=queue,
            dispatcher=dispatcher,
            ranker=ranker,
            organisation=org,
        )

        return scheduler

    def initialize_boefje_schedulers(self) -> None:
        """Initialize the schedulers for the Boefje tasks. We will create
        schedulers for all organisations in the Katalogus service.
        """
        orgs = self.ctx.services.katalogus.get_organisations()
        for org in orgs:
            s = self.create_boefje_scheduler(org)
            self.schedulers[s.scheduler_id] = s

    def create_boefje_scheduler(self, org: Organisation) -> schedulers.BoefjeScheduler:
        """Create a scheduler for the given organisation.

        Args:
            org: The organisation to create a scheduler for.
        """
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
            task_name="tasks.handle_boefje",  # TODO: check this in rbmq
        )

        ranker = rankers.BoefjeRanker(
            ctx=self.ctx,
        )

        scheduler = schedulers.BoefjeScheduler(
            ctx=self.ctx,
            scheduler_id=f"boefje-{org.id}",
            queue=queue,
            dispatcher=dispatcher,
            ranker=ranker,
            organisation=org,
        )

        return scheduler

    # TODO: write tests for this
    def monitor_organisations(self) -> None:
        """Monitor the organisations in the Katalogus service, and add/remove
        organisations from the schedulers.
        """
        scheduler_orgs = set([s.organisation.id for s in self.schedulers.values()])
        katalogus_orgs = set([org.id for org in self.ctx.services.katalogus.get_organisations()])

        additions = katalogus_orgs.difference(scheduler_orgs)
        removals = scheduler_orgs.difference(katalogus_orgs)

        for org_id in removals:
            for s in self.schedulers.values():
                if s.organisation.id != org_id:
                    continue

                del self.schedulers[s.scheduler_id]
                break

        self.logger.info("Removed %s organisations from scheduler [org_ids=%s]", len(removals), removals)

        for org_id in additions:
            org = self.ctx.services.katalogus.get_organisation(org_id)

            scheduler_normalizer = self.create_normalizer_scheduler(org)
            self.schedulers[scheduler_normalizer.scheduler_id] = scheduler_normalizer

            scheduler_boefje = self.create_boefje_scheduler(org)
            self.schedulers[scheduler_boefje.scheduler_id] = scheduler_boefje

        self.logger.info("Added %s organisations to scheduler [org_ids=%s]", len(additions), additions)

    def run(self) -> None:
        """Start the main scheduler application, and run in threads the
        following processes:

            * api server
            * listeners
            * schedulers
            * monitors
            * dispatchers
        """
        # API Server
        self._run_in_thread(name="server", func=self.server.run, daemon=False)

        # Start the listeners
        for name, listener in self.listeners.items():
            self._run_in_thread(name=name, func=listener.listen)

        # Start the schedulers
        for scheduler in self.schedulers.values():
            scheduler.run()

        # Start monitors
        self._run_in_thread(name="monitor_organisations", func=self.monitor_organisations, interval=180)

        # Main thread
        while not self.stop_event.is_set():
            time.sleep(0.01)

        self.shutdown()
