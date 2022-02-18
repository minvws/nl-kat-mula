import heapq
import logging
import queue
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


class PriorityQueue:
    """Thread-safe implementation of a priority queue.

    When a multi-processing implementation is required, see:
    https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Queue

    Reference:
        https://docs.python.org/3/library/queue.html#queue.PriorityQueue
    """

    def __init__(self, id: str, maxsize: int):
        self.logger = logging.getLogger(__name__)
        self.id = id
        self.maxsize = maxsize
        self.pq = queue.PriorityQueue(maxsize=self.maxsize)

    def pop(self) -> Tuple[int, Dict]:
        """Pop the item with the highest priority from the queue. If optional
        args block is true and timeout is None (the default), block if
        necessary until an item is available. If timeout is a positive number,
        it blocks at most timeout seconds and raises the Empty exception if no
        item was available within that time. Otherwise (block is false), return
        an item if one is immediately available, else raise the Empty exception
        (timeout is ignored in that case).

        Reference:
            https://docs.python.org/3/library/queue.html#queue.PriorityQueue.get
        """
        return self.pq.get(block=True, timeout=5)

    def push(self, priority: int, item: Dict):
        self.pq.put(
            item=PrioritizedItem(priority=priority, item=item),
            block=True,
        )

    def json(self) -> Dict:
        return {
            "id": self.id,
            "size": self.pq.qsize(),
            "maxsize": self.maxsize,
            "pq": [self.pq.queue[i].json() for i in range(self.pq.qsize())],  # TODO: maybe overkill
        }

    def __len__(self):
        return self.pq.qsize()


@dataclass(order=True)
class PrioritizedItem:
    """Solves the issue non-comporable tasks to ignore the task item and only
    compare the priority."""

    priority: int
    item: Any = field(compare=False)

    def __init__(self, priority: int, item: Any):
        self.priority = priority
        self.item = item

    def json(self) -> Dict:
        return {"priority": self.priority, "item": self.item}
