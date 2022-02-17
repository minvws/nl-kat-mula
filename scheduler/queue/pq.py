import heapq
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


class PriorityQueue:
    def __init__(self, name: str):
        self.logger = logging.getLogger(__name__)
        self.name = name
        self.pq = []

    def pop(self) -> Tuple[int, Dict]:
        return heapq.heappop(self.pq)

    def push(self, item: Dict, priority: int):
        heapq.heappush(self.pq, PrioritizedItem(priority, item))

    def __len__(self):
        return len(self.pq)


@dataclass(order=True)
class PrioritizedItem:
    """Solves the issue non-comporable tasks to ignore the task item and only
    compare the priority."""

    priority: int
    item: Any = field(compare=False)
