import logging
import os
import threading
import time
import uuid
from typing import Any, Callable, Dict, Optional

from scheduler import (context, dispatchers, queue, queues, ranker, server,
                       thread)
from scheduler.connectors import listeners
from scheduler.models import OOI, Boefje, BoefjeTask, NormalizerTask


class Scheduler:
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

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.ctx = context.AppContext()
        self.threads = {}
        self.stop_event = threading.Event()

        # Initialize queues
        self.queues = {
            "boefjes": queues.BoefjePriorityQueue(
                id="boefjes",
                maxsize=self.ctx.config.pq_maxsize,
                item_type=BoefjeTask,
                allow_priority_updates=True,
            ),
        }

        # Initialize rankers
        self.rankers = {
            "boefjes": ranker.BoefjeRankerTimeBased(
                ctx=self.ctx,
            ),
        }

        # Initialize event stream listeners
        self.listeners = {}

        # Initialize dispatchers
        self.dispatchers = {
            "boefjes": dispatchers.BoefjeDispatcherTimeBased(
                ctx=self.ctx,
                pq=self.queues.get("boefjes"),
                item_type=BoefjeTask,
                queue="boefjes",
                task_name="tasks.handle_boefje",
            ),
        }

        # Initialize API server
        self.server = server.Server(self.ctx, queues=self.queues)

    def shutdown(self) -> None:
        """Gracefully shutdown the scheduler, and all threads."""
        self.logger.warning("Shutting down...")

        for k, t in self.threads.items():
            t.join(timeout=5)

        self.logger.warning("Shutdown complete")

        os._exit(0)

    def _populate_normalizers_queue(self) -> None:
        # TODO: from bytes get boefjes jobs that are done
        self.logger.info("_populate_normalizers_queue")

    def _add_normalizer_task_to_queue(self, task: NormalizerTask) -> None:
        self.queues.get("normalizers").push(
            queue.PrioritizedItem(priority=0, item=task),
        )

    def _populate_boefjes_queue(self) -> None:
        """Process to add boefje tasks to the boefjes priority queue."""
        # oois = self.ctx.services.octopoes.get_random_objects(n=10)
        oois = self.ctx.services.octopoes.get_objects()

        # TODO: make concurrent, since ranker will be doing I/O using external
        # services
        count_tasks = 0
        for ooi in oois:
            score = self.rankers.get("boefjes").rank(ooi)

            # TODO: get boefjes for ooi, active boefjes depend on organization
            # and indemnification?

            # Get available boefjes based on ooi type
            boefjes = self.ctx.services.katalogus.get_boefjes_by_ooi_type(
                ooi.ooi_type,
            )
            if boefjes is None:
                self.logger.debug(f"No boefjes found for type {ooi.ooi_type} [ooi={ooi}]")
                continue

            self.logger.debug(
                f"Found {len(boefjes)} boefjes for ooi {ooi} [ooi={ooi}, boefjes={[boefje.id for boefje in boefjes]}"
            )

            boefjes_queue = self.queues.get("boefjes")
            for boefje in boefjes:
                organization = "_dev"  # FIXME

                task = BoefjeTask(
                    boefje=boefje,
                    input_ooi=ooi.id,
                    organization=organization,
                )

                # When using time-based dispatcher and rankers we don't want
                # the populator to add tasks to the queue, and we do want
                # allow the api to update the priority
                if boefjes_queue.is_item_on_queue(task):
                    self.logger.debug(
                        f"Boefje task already on queue [boefje={boefje.id} input_ooi={ooi.id} organization={organization}]",
                    )
                    continue

                self.queues.get("boefjes").push(
                    queue.PrioritizedItem(priority=score, item=task),
                )
                count_tasks += 1

        if count_tasks > 0:
            self.logger.info(
                f"Added {count_tasks} boefje tasks to queue [queue_id={self.queues.get('boefjes').id}, count_tasks={count_tasks}]",
            )

    def _run_in_thread(
        self, name: str, func: Callable, interval: float = 0.01, daemon: bool = False,
    ) -> None:
        """Make a function run in a thread, and add it to the dict of threads.

        Args:
            name: The name of the thread.
            func: The function to run in the thread.
            daemon: Whether the thread should be a daemon.
            *args: Arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.
        """
        self.threads[name] = thread.ThreadRunner(
            target=func,
            stop_event=self.stop_event,
            interval=interval,
        )
        self.threads[name].setDaemon(daemon)
        self.threads[name].start()

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

        # Queue populators
        #
        # We start the `_populate_{queue_id}_queue` functions in separate
        # threads, and these can be run with a configurable defined interval.
        for k, q in self.queues.items():
            self._run_in_thread(
                name=f"{k}_queue_populator",
                func=getattr(self, f"_populate_{q.id}_queue"),
                interval=self.ctx.config.pq_populate_interval,
            )

        # Dispatchers directing work from queues to workers
        for k, d in self.dispatchers.items():
            self._run_in_thread(name=k, func=d.run, daemon=False, interval=5)

        # Main thread
        while not self.stop_event.is_set():
            time.sleep(0.01)

        self.shutdown()
