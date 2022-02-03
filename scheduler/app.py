import logging

from scheduler import context, server


class Scheduler:
    logger: logging.Logger
    ctx: context.AppContext
    srv: server.Server

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ctx = context.AppContext()
        self.srv = server.Server(self.ctx)

    def run(self):
        self.srv.run()

        self.logger.info("Scheduler started ...")
