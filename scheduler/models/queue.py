import datetime
import uuid
from typing import Any, List

import mmh3
from pydantic import BaseModel
from sqlalchemy import JSON, Column, DateTime, Enum, Integer, String

from scheduler.utils import GUID

from .base import Base


class PrioritizedItem(BaseModel):
    """Representation of an queue.PrioritizedItem on the priority queue. Used
    for unmarshalling of priority queue prioritized items to a JSON
    representation.
    """


    id: uuid.UUID
    scheduler_id: uuid.UUID
    hash: str
    priority: int
    data: Any   # FIXME: enforce json, dict or str?

    created_at: datetime.datetime
    modified_at: datetime.datetime

    class Config:
        orm_mode = True


class Queue(BaseModel):
    """Representation of an queue.PriorityQueue object. Used for unmarshalling
    of priority queues to a JSON representation.
    """

    id: str
    size: int
    maxsize: int
    allow_replace: bool
    allow_updates: bool
    allow_priority_updates: bool
    pq: List[PrioritizedItem]


class PrioritizedItemORM(Base):
    """Representation of an queue.PrioritizedItem on the priority queue. Used
    for marshalling of priority queue prioritized items to a database
    representation.
    """

    __tablename__ = "items"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = uuid.uuid4().hex

    id = Column(GUID, primary_key=True)
    scheduler_id = Column(GUID)
    hash = Column(String)

    priority = Column(Integer)
    data = Column(JSON, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.datetime.utcnow,
    )
    modified_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
