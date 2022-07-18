import datetime
import uuid
from enum import Enum as _Enum
from json import JSONEncoder
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from scheduler.utils import GUID

from .base import Base
from .boefje import Boefje, BoefjeMeta
from .normalizer import Normalizer
from .queue import QueuePrioritizedItem


class TaskStatus(_Enum):
    """Status of a task."""

    QUEUED = "queued"
    PENDING = "pending"
    RUNNING = "running"  # TODO: dispatched
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    task: QueuePrioritizedItem
    status: TaskStatus
    created_at: datetime.datetime
    modified_at: datetime.datetime

    class Config:
        orm_mode = True


class TaskORM(Base):
    __tablename__ = "tasks"

    # id = Column(UUID(as_uuid=True), primary_key=True)
    # scheduler_id=Column(UUID, ForeignKey("schedulers.id"))
    id = Column(GUID, primary_key=True)
    scheduler_id = Column(GUID)
    task: JSON = Column(JSON, nullable=False)
    status: TaskStatus = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.now)
    modified_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.now)


class NormalizerTask(BaseModel):
    """NormalizerTask represent data needed for a Normalizer to run."""

    id: Optional[str]
    normalizer: Normalizer
    boefje_meta: BoefjeMeta

    def __hash__(self):
        """Make NormalizerTask hashable, so that we can de-duplicate it when
        used in the PriorityQueue. We hash the combination of the attributes
        normalizer.id since this combination is unique."""
        return hash((self.normalizer.id, self.boefje_meta.id))


class BoefjeTask(BaseModel):
    """BoefjeTask represent data needed for a Boefje to run."""

    id: Optional[str]
    boefje: Boefje
    input_ooi: str
    organization: str

    dispatches: List[Normalizer] = Field(default_factory=list)

    def __hash__(self) -> int:
        """Make BoefjeTask hashable, so that we can de-duplicate it when used
        in the PriorityQueue. We hash the combination of the attributes
        input_ooi and boefje.id since this combination is unique."""
        return hash((self.input_ooi, self.boefje.id, self.organization))
