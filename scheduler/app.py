import logging
import threading
from typing import Dict

from scheduler import connector, context, queue, ranker, server
from scheduler.connector import listener
from scheduler.models import OOI, BoefjeMeta


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

    def _populate_boefjes_queue(self):
        # TODO: get random set of OOI's, choice needs to be made to get this
        # from octopoes, xtb, or from internal storage

        oois = self.ctx.services.xtdb.get_random_oois(n=3)  # FIXME: configurable
        self.logger.info(oois)

        # TODO: decide if it is necessary to create models from the data, since
        # now it is O(n) and we can use the data directly
        # oois = [OOI.parse_obj(o) for o in objects]

        # TODO: rank the OOI's (or create jobs (oois*boefjes=tasks) and then
        # rank?)
        # TODO: make concurrent, since ranker will be doing I/O using external
        # services
        for ooi in oois:
            score = self.boefjes_ranker.rank(ooi)
            # boefje_meta = BoefjeMeta()
            boefje_meta = ooi
            self.boefjes_queue.push(item=boefje_meta, priority=score)

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
