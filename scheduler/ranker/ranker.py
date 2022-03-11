import logging
import time

from scheduler import context, models


class Ranker:
    logger: logging.Logger
    ctx: context.AppContext

    def __init__(self, ctx):
        self.logger = logging.getLogger(__name__)
        self.ctx = ctx

    def rank(self, ooi: models.OOI) -> int:
        raise NotImplementedError()


class BoefjeRanker(Ranker):
    def rank(self, ooi: models.OOI) -> int:
        return time.time() - 86400


class NormalizerRanker(Ranker):
    pass
