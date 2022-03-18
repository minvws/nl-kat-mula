import logging
import os
import threading
import time
import uuid
from typing import Callable, Dict

from scheduler import context, dispatcher, queue, ranker, server, thread
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

    logger: logging.Logger
    ctx: context.AppContext
    listeners: Dict[str, listeners.Listener]
    queues: Dict[str, queue.PriorityQueue]
    server: server.Server
    threads: Dict[str, threading.Thread]
    stop_event: threading.Event

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ctx = context.AppContext()
        self.threads = {}
        self.stop_event = threading.Event()

        # Initialize queues
        self.queues = {
            "boefjes": queue.PriorityQueue(
                id="boefjes",
                maxsize=self.ctx.config.pq_maxsize,
                item_type=BoefjeTask,
            ),
            "normalizers": queue.PriorityQueue(
                id="normalizers",
                maxsize=self.ctx.config.pq_maxsize,
                item_type=NormalizerTask,
            ),
        }

        # Initialize rankers
        self.rankers = {
            "boefjes": ranker.BoefjeRanker(
                ctx=self.ctx,
            ),
            "normalizers": ranker.NormalizerRanker(
                ctx=self.ctx,
            ),
        }

        # Initialize event stream listeners
        self.listeners = {
            "create_event": listeners.CreateEventListener(
                dsn=self.ctx.config.lst_octopoes,
                queue="create_events",  # FIXME: queue name should be configurable
                ctx=self.ctx,
                normalizer_queue=self.queues.get("normalizers"),
            ),
        }

        # Initialize dispatchers
        self.dispatchers = {
            "boefjes": dispatcher.BoefjeDispatcher(
                ctx=self.ctx,
                pq=self.queues.get("boefjes"),
                item_type=BoefjeTask,
                queue="boefjes",
                task_name="tasks.handle_boefje",
            ),
        }

        # Initialize API server
        self.server = server.Server(self.ctx, queues=self.queues)

    def shutdown(self):
        """Gracefully shutdown the scheduler, and all threads."""
        self.logger.warning("Shutting down...")

        for k, t in self.threads.items():
            t.join(timeout=5)

        self.logger.warning("Shutdown complete")

        os._exit(0)

    def _populate_normalizers_queue(self):
        # TODO: from bytes get boefjes jobs that are done
        self.logger.info("_populate_normalizers_queue")

    def _add_normalizer_task_to_queue(self, task: NormalizerTask):
        self.queues.get("normalizers").push(
            queue.PrioritizedItem(priority=0, item=task),
        )

    def _populate_boefjes_queue(self):
        """Process to add boefje tasks to the boefjes priority queue."""
        # TODO: get n from config file
        oois = self.ctx.services.octopoes.get_objects()
        # oois = self.ctx.services.xtdb.get_random_objects(n=3)

        # TODO: make concurrent, since ranker will be doing I/O using external
        # services
        for ooi in oois:
            score = self.rankers.get("boefjes").rank(ooi)

            # TODO: get boefjes for ooi, active boefjes depend on organization
            # and indemnification?

            # Get available boefjes based on ooi type
            boefjes = self.ctx.services.katalogus.cache_ooi_type.get(
                ooi.ooi_type,
                None,
            )
            if boefjes is None:
                self.logger.warning(f"No boefjes found for type {ooi.ooi_type} [ooi={ooi}]")
                continue

            self.logger.info(
                f"Found {len(boefjes)} boefjes for ooi_type {ooi.ooi_type} [ooi={ooi} boefjes={[boefje.id for boefje in boefjes]}"
            )

            for boefje in boefjes:
                task = BoefjeTask(
                    id=uuid.uuid4().hex,
                    boefje=boefje,
                    input_ooi=ooi.reference,
                    organization=ooi.organization,
                )

                # TODO: do we have a grace period for boefjes that have been
                # running for this ooi too soon?

                self.queues.get("boefjes").push(
                    queue.PrioritizedItem(priority=score, item=task),
                )

    def _run_in_thread(self, name: str, func: Callable, interval: float = 0.01, daemon: bool = False, *args, **kwargs):
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
            args=args,
            kwargs=kwargs,
        )
        self.threads[name].setDaemon(daemon)
        self.threads[name].start()

    def run(self):
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

        # Queue population
        #
        # We start the `_populate_{queue_id}_queue` functions in separate
        # threads, and these can be run with a configurable defined interval.
        for k, q in self.queues.items():
            self._run_in_thread(
                name=f"{k}_queue_populator",
                func=getattr(self, f"_populate_{q.id}_queue"),
            )

        # Dispatchers directing work from queues to workers
        for k, d in self.dispatchers.items():
            self._run_in_thread(name=k, func=d.run, daemon=False)

        # Main thread
        while not self.stop_event.is_set():
            time.sleep(0.01)

        self.shutdown()
