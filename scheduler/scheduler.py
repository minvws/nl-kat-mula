import logging
import threading
import time
from typing import Callable, Dict

from scheduler import context, dispatcher, queue, ranker, server
from scheduler.connectors import listeners
from scheduler.models import OOI, Boefje, BoefjeTask, NormalizerTask


class Scheduler:
    logger: logging.Logger
    ctx: context.AppContext
    listeners: Dict[str, listeners.Listener]
    queues: Dict[str, queue.PriorityQueue]
    server: server.Server

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ctx = context.AppContext()

        # Initialize message bus listeners
        self.listeners = {
            "octopoes_listener": listeners.Octopoes(
                dsn=self.ctx.config.lst_octopoes,
                queue="create_events",  # FIXME: queue name should be configurable
            ),
        }

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

        # Initialize API server
        self.server = server.Server(self.ctx, queues=self.queues)

    # TODO: add shutdown hook for graceful shutdown of threads, when exceptions
    # occur
    def shutdown(self):
        pass

    def loop_with_interval(self, interval: int, func: Callable):
        while True:
            func()
            time.sleep(interval)

    def _populate_normalizers_queue(self):
        # TODO: from bytes get boefjes jobs that are done
        self.logger.info("_populate_normalizers_queue")

    def _add_normalizer_task_to_queue(self, task: NormalizerTask):
        self.queues.get("normalizers").push(
            queue.PrioritizedItem(priority=0, item=task),
        )

    def _populate_boefjes_queue(self):
        # TODO: get n from config file
        # oois = self.ctx.services.octopoes.get_random_objects(n=3)
        oois = self.ctx.services.octopoes.get_objects()

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
                    boefje=boefje,
                    input_ooi="derp",  # FIXME
                    arguments={},  # FIXME
                    organization="_dev",  # FIXME
                )

                self._add_boefje_task_to_queue(task)

    def _add_boefje_task_to_queue(self, task: BoefjeTask):
        self.queues.get("boefjes").push(
            queue.PrioritizedItem(priority=0, item=task),
        )

    def run(self):
        # TODO: all threads in a list?

        # API server
        th_server = threading.Thread(target=self.server.run)
        th_server.setDaemon(True)
        th_server.start()

        # Listeners for OOI changes
        for _, l in self.listeners.items():
            th_listener = threading.Thread(target=l.listen)
            th_listener.setDaemon(True)
            th_listener.start()

        # Queue population
        #
        # We start the `_populate_{queue_id}_queue` functions in a separate
        # threads, and these be run with an configurable defined interval.

        # TODO: do we want to do it like this, will there be queues without
        # a specific population based on an id?
        for _, q in self.queues.items():
            th_queue = threading.Thread(
                target=self.loop_with_interval,
                kwargs={
                    "interval": self.ctx.config.pq_populate_interval,
                    "func": getattr(self, f"_populate_{q.id}_queue"),
                },
            )
            th_queue.setDaemon(True)
            th_queue.start()

        # Dispatchers directing work from queues to workers
        dispatcher.CeleryDispatcher(
            ctx=self.ctx,
            pq=self.queues.get("boefjes"),
            queue="boefjes",
            task_name="tasks.handle_boefje",
        ).run()

        self.logger.info("Scheduler started ...")

        while True:
            pass
