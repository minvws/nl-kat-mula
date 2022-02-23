import heapq
import json
import logging
import queue
from dataclasses import dataclass, field
from typing import Any, Dict, Set, Tuple

import pydantic


@dataclass(order=True)
class PrioritizedItem:
    """Solves the issue non-comparable tasks to ignore the task item and only
    compare the priority."""

    priority: int
    item: Any = field(compare=False)

    def __init__(self, priority: int, item: Any):
        self.priority = priority
        self.item = item

    def dict(self) -> Dict:
        return {"priority": self.priority, "item": self.item}

    def json(self) -> str:
        return json.dumps(self.dict())

    def __hash__(self):
        return hash(self.item)

    def __eq__(self, other):
        return self.item == other.item


class PriorityQueue:
    """Thread-safe implementation of a priority queue.

    When a multi-processing implementation is required, see:
    https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Queue

    Reference:
        https://docs.python.org/3/library/queue.html#queue.PriorityQueue
    """

    logger: logging.Logger
    id: str
    maxsize: int
    item_type: pydantic.BaseModel
    pq: queue.PriorityQueue
    timeout: int = 5
    item_set: Set[PrioritizedItem] = set()

    def __init__(self, id: str, maxsize: int, item_type: pydantic.BaseModel):
        self.logger = logging.getLogger(__name__)
        self.id = id
        self.maxsize = maxsize
        self.item_type = item_type
        self.pq = queue.PriorityQueue(maxsize=self.maxsize)

    def pop(self) -> PrioritizedItem:
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
        item = self.pq.get(block=True, timeout=self.timeout)
        self.item_set.remove(item)
        return item

    def push(self, p_item: PrioritizedItem) -> None:
        """Push an item with priority into the queue. When timeout is set it
        will block if necessary until a free slot is available. It raises the
        Full exception if no free slot was available within that time.

        Args:
            p_item: The item to be pushed into the queue.

        Raises:
            ValueError: If the item is not valid.

        Reference:
            https://docs.python.org/3/library/queue.html#queue.PriorityQueue.put
        """
        if p_item in self.item_set:
            self.logger.warning(f"Item {p_item} already exists in the queue. Ignoring the item.")
            return

        if not self._is_valid_item(p_item.item):
            raise ValueError(f"PrioritizedItem must be of type {self.item_type.__name__}")

        self.pq.put(
            item=p_item,
            block=True,
            timeout=self.timeout,
        )
        self.item_set.add(p_item)

    def _is_valid_item(self, item: Any) -> bool:
        """Validate the item to be pushed into the queue.

        Args:
            item: The item to be validated.

        Returns:
            bool: True if the item is valid, False otherwise.
        """
        try:
            pydantic.parse_obj_as(self.item_type, item)
        except pydantic.ValidationError:
            return False

        return True

    def dict(self) -> Dict:
        return {
            "id": self.id,
            "size": self.pq.qsize(),
            "maxsize": self.maxsize,
            "pq": [self.pq.queue[i].dict() for i in range(self.pq.qsize())],  # TODO: maybe overkill
        }

    def json(self) -> str:
        return json.dumps(self.dict())

    def empty(self) -> bool:
        return self.pq.empty()

    def __len__(self):
        return self.pq.qsize()
