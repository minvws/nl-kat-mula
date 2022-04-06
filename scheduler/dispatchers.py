import time

from scheduler import dispatcher


class BoefjeDispatcher(dispatcher.CeleryDispatcher):
    pass


class BoefjeDispatcherTimeBased(dispatcher.CeleryDispatcher):
    """A time-based BoefjeDispatcher allows for executing jobs at a certain
    time. The threshold of dispatching jobs is the current time, and based
    on the time-based priority score of the jobs on the queue. The dispatcher
    determines to dispatch the job.
    """

    def get_threshold(self) -> int:
        return int(time.time())
