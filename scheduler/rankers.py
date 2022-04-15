import random
from datetime import datetime, timedelta
from typing import Any

from scheduler import ranker


class BoefjeRanker(ranker.Ranker):
    def rank(self, obj: Any) -> int:
        return random.randint(2, 100)


class BoefjeRankerTimeBased(ranker.Ranker):
    """A timed-based BoefjeRanker allows for a specific time to be set for the
    task to be ranked. In combination with a time-based dispatcher. You'll be
    able to rank jobs with a specific time element. Epoch time is used allows
    the score and used as the priority on the priority queue. This allows for
    time-based scheduling of jobs.
    """

    def rank(self, obj: Any) -> int:
        minimum = datetime.today() + timedelta(days=1)
        maximum = minimum + timedelta(days=7)
        return random.randint(int(minimum.timestamp()), int(maximum.timestamp()))
