from typing import Any, List

from pydantic import BaseModel


class QueueItem(BaseModel):
    priority: int
    item: Any


class Queue(BaseModel):
    id: str
    size: int
    maxsize: int
    pq: List[QueueItem]
