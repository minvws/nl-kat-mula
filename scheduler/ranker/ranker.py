import logging
import random
from datetime import datetime, timedelta

from scheduler import context, models


class Ranker:
    def __init__(self, ctx: context.AppContext) -> None:
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.ctx: context.AppContext = ctx

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
        minimum = datetime.today() + timedelta(days=1)
        maximum = minimum + timedelta(days=7)
        return random.randint(int(minimum.timestamp()), int(maximum.timestamp()))


class NormalizerRanker(Ranker):
    pass
