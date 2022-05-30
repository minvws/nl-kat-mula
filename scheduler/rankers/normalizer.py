from datetime import datetime, timezone
from typing import Any

from .ranker import Ranker


class NormalizerRanker(Ranker):
    """Ranking of NormalizerTasks
    """

    def rank(self, obj: Any) -> int:
        # Features:
        # * how many findings with mime_type and normalizer
        return int(datetime.now(timezone.utc).timestamp())
