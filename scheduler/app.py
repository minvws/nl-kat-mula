from scheduler import context


class Scheduler:
    ctx: context.AppContext

    def __init__(self):
        self.ctx = context.AppContext()

    def run(self):
        self.ctx.logger.info("Scheduler started ...")
