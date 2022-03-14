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
        return 2


class BoefjeRankerTimeBased(Ranker):
    """A timed-based BoefjeRanker allows for a specific time to be set for the
    task to be ranked. In combination with a time-based dispatcher. You'll be
    able to rank jobs with a specific time element. Epoch time is used allows
    the score and used as the priority on the priority queue. This allows for
    time-based scheduling of jobs.
    """

    def rank(self, ooi: models.OOI) -> int:
        return time.time() + 86400


class NormalizerRanker(Ranker):
    pass
