import math
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from .ranker import Ranker


class BoefjeRanker(Ranker):
    def rank(self, obj: Any) -> int:
        """When a task hasn't run in a while it needs to be run sooner. We
        want a task to get a priority of 3 when `max_days` days are gone by,
        and thus it should have a lower bound of 3 for every day past those
        `max_days`. This is because priority 0 is reserved for rocky tasks,
        priority 2 is reserved for tasks that have not run yet for created
        ooi's.

        So everything before those `max_days` to the grace period are given a
        priority from `maxsize` of the queue, up from 3. We calculate
        the priority starting from the `grace_period`, so we subtract that
        from our time delta between now and the `last_run` of the object
        onwards, since it everything before the `grace_period` won't be
        regarded anyway. So from that initial point (the end of the
        `grace_period`, x=0) we want to place the priority the lowest, thus
        the last place in the queue) which is our `maxsize`.

        Since we want to have a lower bound of a priority of 3, we will use
        an exponential decay function in decreasing form.
        """
        if obj.last_run_boefje is None:
            return 2

        max_size = self.ctx.config.pq_maxsize
        grace_period = timedelta(seconds=self.ctx.config.pq_populate_grace_period)

        # How many after grace period should the priority be 3
        max_days = 7 * (60 * 60 * 24)

        run_since_grace_period = ((datetime.now(timezone.utc) - obj.last_run_boefje.ended_at) - grace_period).seconds
        if run_since_grace_period < 0:
            return -1

        y = max_size * math.pow(math.e, -(math.log(1000) / max_days) * run_since_grace_period) + 2

        return int(y)


class BoefjeRankerTimeBased(Ranker):
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
