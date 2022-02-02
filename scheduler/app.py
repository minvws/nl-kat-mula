import logging

from scheduler import context


class Scheduler:
    logger: logging.Logger
    ctx: context.AppContext

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ctx = context.AppContext()

    def run(self):
        self.logger.info("Scheduler started ...")
