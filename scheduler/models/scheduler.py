from typing import Any, Dict

from pydantic import BaseModel

from scheduler.models import Queue


class Scheduler(BaseModel):
    """Representation of a schedulers.Scheduler instance. Used for
    unmarshalling of schedulers to a JSON representation."""
    id: str
    populate_queue_enabled: bool
    priority_queue: Dict[str, Any]
