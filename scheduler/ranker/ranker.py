import logging

from scheduler import context, models


class Ranker:
    logger: logging.Logger
    ctx: context.AppContext

    def __init__(self, ctx):
        self.logger = logging.getLogger(__name__)
        self.ctx = ctx

    def rank(self, ooi: models.OOI) -> int:
        return 1


class BoefjeRanker(Ranker):
    pass


class NormalizerRanker(Ranker):
    pass
