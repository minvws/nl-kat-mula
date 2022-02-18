import heapq
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


class PriorityQueue:
    def __init__(self, id: str, max_size: str):
        self.logger = logging.getLogger(__name__)
        self.id = id
        self.max_size = max_size
        self.pq = []

    def pop(self) -> Tuple[int, Dict]:
        return heapq.heappop(self.pq)

    def push(self, item: Dict, priority: int):
        heapq.heappush(self.pq, PrioritizedItem(priority, item))

    def json(self) -> Dict:
        return {
            "id": self.id,
            "size": len(self.pq),
            "max_size": len(self.pq),
            "pq": [item.json() for item in self.pq],
        }

    def __len__(self):
        return len(self.pq)


@dataclass(order=True)
class PrioritizedItem:
    """Solves the issue non-comporable tasks to ignore the task item and only
    compare the priority."""

    priority: int
    item: Any = field(compare=False)

    def json(self) -> Dict:
        return {"priority": self.priority, "item": self.item}
