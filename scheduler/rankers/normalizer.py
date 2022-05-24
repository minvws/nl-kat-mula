from datetime import datetime, timezone
from typing import Any

from .ranker import Ranker


class NormalizerRanker(Ranker):
    """Ranking of NormalizerTasks

    Using timestamp of an incoming job, to resemble a FIFO queue.
    """
    def rank(self, obj: Any) -> int:
        return int(datetime.now(timezone.utc).timestamp())
