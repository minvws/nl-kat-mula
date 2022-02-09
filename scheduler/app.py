import logging
import threading

from scheduler import connector, context, server
from scheduler.connector import listener
from scheduler.models import OOI


class Scheduler:
    logger: logging.Logger
    ctx: context.AppContext
    srv: server.Server

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ctx = context.AppContext()

        # API server
        self.srv = server.Server(self.ctx)

        # Active message bus listeners
        self.lst = listener.RabbitMQ(
            dsn=self.ctx.config.queue_uri,
            queue="create_events",  # FIXME: queue name should be configurable
        )

        # Initialize queues
        self.boefjes_queue = None
        self.normalizers_queue = None

        self._populate_boefjes_queue()

    # TODO: add shutdown hook for graceful shutdown of threads, when exceptions
    # occur

    def _populate_boefjes_queue(self):
        # TODO: get random set of OOI's
        # TODO: choice needs to be made to get this from octopoes, xtb, or
        # from internal storage
        # TODO: decide if it is necessary to create models from the data
        objects = self.ctx.services.octopoes.get_random_oois()
        self.logger.info(objects)
        oois = [OOI.parse_obj(o) for o in objects]

        self.logger.info("Populating boefjes queue with %d objects", len(oois))

        # TODO: rank the OOI's (or create jobs and then rank?)

        # TODO: push to queue

        pass

    def run(self):
        th_server = threading.Thread(target=self.srv.run)
        th_listener = threading.Thread(target=self.lst.listen)

        th_server.setDaemon(True)
        th_listener.setDaemon(True)

        th_server.start()
        th_listener.start()

        self.logger.info("Scheduler started ...")

        while True:
            pass
