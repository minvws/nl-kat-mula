from typing import Any

from .ranker import Ranker


class NormalizerRanker(Ranker):
    def rank(self, obj: Any) -> int:
        return 1
