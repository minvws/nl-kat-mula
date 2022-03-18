from typing import Any, List

from pydantic import BaseModel


class QueueItem(BaseModel):
    """Representation of an queue.PrioritizedItem on the priority queue. Used
    for unmarshalling of priority queue items to a JSON representation.
    """

    priority: int
    item: Any


class Queue(BaseModel):
    """Representation of an queue.PriorityQueue object. Used for unmarshalling
    of priority queues to a JSON representation.
    """

    id: str
    size: int
    maxsize: int
    pq: List[QueueItem]
