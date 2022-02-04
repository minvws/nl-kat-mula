import logging
import threading

from scheduler import connector, context, server
from scheduler.connector import listener


class Scheduler:
    logger: logging.Logger
    ctx: context.AppContext
    srv: server.Server

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ctx = context.AppContext()
        self.srv = server.Server(self.ctx)

        # TODO: could be more listeners coming
        self.lst = listener.RabbitMQ(
            dsn=self.ctx.config.queue_uri,
            queue="create_events",  # FIXME: queue name should be configurable
        )

    # TODO: add shutdown hook for graceful shutdown of threads

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
