import logging
import threading
from typing import Dict

from scheduler import connector, context, queue, ranker, server
from scheduler.connector import listener
from scheduler.models import OOI, Boefje, BoefjeTask


class Scheduler:
    logger: logging.Logger
    ctx: context.AppContext
    server: server.Server
    listeners: Dict[str, listener.Listener]

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ctx = context.AppContext()

        # API server
        self.server = server.Server(self.ctx)

        # FIXME: remove
        def hello():
            self.logger.info("hello, world")

        # Active message bus listeners
        self.listeners = {
            "octopoes_listener": listener.RabbitMQ(
                func=hello,
                dsn=self.ctx.config.queue_uri,
                queue="create_events",  # FIXME: queue name should be configurable
            ),
        }

        # Initialize queues
        self.boefjes_queue = queue.PriorityQueue()
        self.normalizers_queue = queue.PriorityQueue()

        # Initialize rankers
        self.boefjes_ranker = ranker.BoefjeRanker(self.ctx)
        self.normalizers_ranker = ranker.NormalizerRanker(self.ctx)

    # TODO: add shutdown hook for graceful shutdown of threads, when exceptions
    # occur
    def shutdown(self):
        pass

    def _populate_boefjes_queue(self):

        # TODO: get n from config file
        # oois = self.ctx.services.octopoes.get_random_objects(n=3)
        oois = self.ctx.services.octopoes.get_objects()

        # TODO: decide if it is necessary to create models from the data, since
        # now it is O(n) and we can use the data directly
        # oois = [OOI.parse_obj(o) for o in objects]
        # TODO: rank the OOI's (or create jobs (ooi*boefje=tasks) and then
        # rank?)
        # TODO: make concurrent, since ranker will be doing I/O using external
        # services
        for ooi in oois:
            score = self.boefjes_ranker.rank(ooi)

            # TODO: get boefjes for ooi, active boefjes depend on organization
            # TODO: boefje filtering on ooi type?
            ooi_type = ooi.get("ooi_type")
            if ooi_type is None:
                self.logger.warning(f"No type for ooi [ooi={ooi}]")
                continue

            # Get available boefjes based on ooi type
            boefjes = self.ctx.services.katalogus.cache_ooi_type.get(ooi_type, None)
            if boefjes is None:
                self.logger.warning(f"No boefjes found for type {ooi_type} [ooi={ooi}]")
                continue

            self.logger.info(
                f"Found {len(boefjes)} boefjes for ooi_type {ooi_type} [ooi={ooi} boefjes={[boefje.get('id') for boefje in boefjes]}"
            )

            for boefje in boefjes:
                task = BoefjeTask(
                    boefje=Boefje(
                        name=boefje.get("name"),
                        # version=boefje.get("version"),
                    ),
                    input_ooi="derp",  # FIXME
                    arguments={},  # FIXME
                    organization="_dev",  # FIXME
                )
                self.boefjes_queue.push(item=task, priority=score)

    def run(self):
        th_server = threading.Thread(target=self.server.run)
        th_server.setDaemon(True)
        th_server.start()

        for _, l in self.listeners.items():
            th_listener = threading.Thread(target=l.listen)
            th_listener.setDaemon(True)
            th_listener.start()

        # TODO: need to be continuous, with a parameter for the interval
        self._populate_boefjes_queue()

        self.logger.info("Scheduler started ...")

        while True:
            pass
