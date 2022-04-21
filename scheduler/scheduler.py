import datetime
import logging
import os
import threading
import time
import uuid
from typing import Any, Callable, Dict

import requests

from scheduler import context, dispatcher, dispatchers, queue, queues, ranker, rankers, server
from scheduler.connectors import listeners
from scheduler.models import BoefjeTask
from scheduler.utils import thread


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

    def __init__(self, ctx: context.AppContext) -> None:
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.ctx: context.AppContext = ctx
        self.threads: Dict[str, thread.ThreadRunner] = {}
        self.stop_event: threading.Event = threading.Event()

        # Initialize queues
        self.queues: Dict[str, queue.PriorityQueue] = {
            "boefjes": queues.BoefjePriorityQueue(
                pq_id="boefjes",
                maxsize=self.ctx.config.pq_maxsize,
                item_type=BoefjeTask,
                allow_priority_updates=True,
            ),
        }

        # Initialize rankers
        self.rankers: Dict[str, ranker.Ranker] = {
            "boefjes": rankers.BoefjeRanker(
                ctx=self.ctx,
            ),
        }

        # Initialize event stream listeners
        self.listeners: Dict[str, listeners.Listener] = {}

        # Initialize dispatchers
        boefjes_queue = self.queues.get("boefjes")
        if boefjes_queue is None:
            raise RuntimeError("No boefjes queue found")

        self.dispatchers: Dict[str, dispatcher.Dispatcher] = {
            "boefjes": dispatchers.BoefjeDispatcher(
                ctx=self.ctx,
                pq=boefjes_queue,
                item_type=BoefjeTask,
                celery_queue="boefjes",
                task_name="tasks.handle_boefje",
            ),
        }

        # Initialize API server
        self.server: server.Server = server.Server(self.ctx, queues=self.queues)

    def shutdown(self) -> None:
        """Gracefully shutdown the scheduler, and all threads."""
        self.logger.warning("Shutting down...")

        for _, t in self.threads.items():
            t.join(timeout=5)

        self.logger.warning("Shutdown complete")

        os._exit(0)

    def _populate_normalizers_queue(self) -> None:
        raise NotImplementedError()

    def _populate_boefjes_queue(self) -> None:
        """Process to add boefje tasks to the boefjes priority queue."""
        tasks_count = 0

        boefjes_queue = self.queues.get("boefjes")
        if boefjes_queue is None:
            raise RuntimeError("No boefjes queue found")

        boefjes_ranker = self.rankers.get("boefjes")
        if boefjes_ranker is None:
            raise RuntimeError("No boefjes ranker found")

        orgs = self.ctx.services.katalogus.get_organisations()
        for org in orgs:

            # oois = self.ctx.services.octopoes.get_random_objects(org=org, n=10)
            try:
                oois = self.ctx.services.octopoes.get_objects(organisation_id=org.id)
            except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                self.logger.warning("Could not get objects for organisation %s [org_id=%s]", org.name, org.id)
                continue

            for ooi in oois:
                try:
                    boefjes = self.ctx.services.katalogus.get_boefjes_by_ooi_type(
                        ooi.ooi_type,
                    )
                except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                    self.logger.warning(
                        "Could not get boefjes for ooi_type %s [ooi_type=%s]", ooi.ooi_type, ooi.ooi_type
                    )
                    continue

                if boefjes is None:
                    self.logger.debug(
                        "No boefjes found for type %s [ooi=%s]",
                        ooi.ooi_type,
                        ooi,
                    )
                    continue

                self.logger.debug(
                    "Found %s boefjes for ooi %s [ooi=%s, boefjes=%s}",
                    len(boefjes),
                    ooi,
                    ooi,
                    [boefje.id for boefje in boefjes],
                )

                for boefje in boefjes:
                    try:
                        plugin = self.ctx.services.katalogus.get_plugin_by_org_and_boefje_id(
                            organisation_id=org.id,
                            boefje_id=boefje.id,
                        )
                    except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                        self.logger.warning(
                            "Could not get plugin for org %s and boefje %s [org_id=%s, boefje_id=%s]",
                            org.name,
                            boefje.name,
                            org.id,
                            boefje.name,
                        )
                        continue

                    if plugin is None:
                        self.logger.debug(
                            "No plugin found for boefje %s [org=%s, boefje=%s]",
                            boefje.id,
                            org.id,
                            boefje.id,
                        )
                        continue

                    if plugin.enabled is False:
                        self.logger.debug("Boefje %s is disabled", boefje.id)
                        continue

                    task = BoefjeTask(
                        id=uuid.uuid4().hex,
                        boefje=boefje,
                        input_ooi=ooi.id,
                        organization=org.id,
                    )

                    ooi_scan_level = ooi.scan_profile.level
                    if ooi_scan_level is None:
                        self.logger.warning(
                            "No scan level found for ooi %s [ooi=%s]",
                            ooi.id,
                            ooi,
                        )
                        continue

                    boefje_scan_level = boefje.scan_level
                    if boefje_scan_level is None:
                        self.logger.warning(
                            "No scan level found for boefje %s [boefje=%s]",
                            boefje.id,
                            boefje,
                        )
                        continue

                    # Boefje intensity score, ooi clearance level, range
                    # from 0 to 4. 0 being the highest intensity, and 4 being
                    # the lowest.
                    if boefje_scan_level < ooi_scan_level:
                        self.logger.debug(
                            "Boefje %s scan level %s is too intense for ooi %s scan level %s [boefje_id=%s, ooi_id=%s]",
                            boefje.id,
                            boefje_scan_level,
                            ooi.id,
                            ooi_scan_level,
                            boefje.id,
                            ooi.id,
                        )
                        continue

                    # We don't want the populator to add/update tasks to the
                    # queue, when they are already on there. However, we do
                    # want to allow the api to update the priority. So we
                    # created the queue with allow_priority_updates=True
                    # regardless. When the ranker is updated to correctly rank
                    # tasks, we can allow the populator to also update the
                    # priority. Then remove the following:
                    if boefjes_queue.is_item_on_queue(task):
                        self.logger.debug(
                            "Boefje task already on queue [boefje=%s, input_ooi=%s, organization=%s]",
                            boefje.id,
                            ooi.id,
                            org.id,
                        )
                        continue

                    # Boefjes should not run before the grace period ends
                    try:
                        last_run_boefje = self.ctx.services.bytes.get_last_run_boefje(
                            boefje_id=boefje.id,
                            input_ooi=ooi.id,
                            organization_id=org.id,
                        )
                    except (requests.exceptions.RetryError, requests.exceptions.ConnectionError):
                        self.logger.warning(
                            "Could not get last run boefje for boefje: '%s' with ooi: '%s' [boefje_id=%s, ooi_id=%s, org_id=%s]",
                            boefje.name,
                            ooi.id,
                            boefje.id,
                            ooi.id,
                            org.id,
                        )
                        continue

                    if (
                        last_run_boefje is not None
                        and datetime.datetime.now().astimezone() - last_run_boefje.ended_at
                        < datetime.timedelta(seconds=self.ctx.config.pq_populate_grace_period)
                    ):
                        self.logger.debug(
                            "Boefje %s already run for input ooi %s [last_run_boefje=%s]",
                            boefje.id,
                            ooi.id,
                            last_run_boefje,
                        )
                        continue

                    score = boefjes_ranker.rank(task)
                    boefjes_queue.push(
                        queue.PrioritizedItem(priority=score, item=task),
                    )

                    tasks_count += 1

        if tasks_count > 0:
            self.logger.info(
                "Added %s boefje tasks to queue [queue_id=%s, tasks_count=%s]",
                tasks_count,
                boefjes_queue.pq_id,
                tasks_count,
            )

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
                func=getattr(self, f"_populate_{q.pq_id}_queue"),
                interval=self.ctx.config.pq_populate_interval,
            )

        # Dispatchers directing work from queues to workers
        for k, d in self.dispatchers.items():
            self._run_in_thread(
                name=k,
                func=d.run,
                daemon=False,
                interval=self.ctx.config.dsp_interval,
            )

        # Main thread
        while not self.stop_event.is_set():
            time.sleep(0.01)

        self.shutdown()
