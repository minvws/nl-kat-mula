import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from scheduler.models import Base


class Boefje(BaseModel):
    id: str
    name: str
    description: str
    version: Optional[str] = Field(default=None)
    scan_level: Optional[int] = Field(default=None)
    consumes: List[str]
    produces: List[str]
    dispatches: Optional[Dict[str, List[str]]] = Field(default=None)


class Normalizer(BaseModel):
    name: str
    version: Optional[str] = Field(default=None)


# TODO: this definition should only be the minimal information for
# a boefje in order to run a task
class BoefjeTask(BaseModel):
    """BoefjeTask represent data needed for a Boefje to run."""

    id: str = uuid.uuid4().hex  # FIXME: this will always be the same!!!
    boefje: Boefje
    input_ooi: str
    organization: str

    dispatches: List[Normalizer] = Field(default_factory=list)

    def __hash__(self):
        """Make BoefjeTask hashable, so that we can deduplicate it when used
        in the PriorityQueue. We hash the combination of the attributes
        input_ooi and boefje.id since this combination is unique."""
        return hash((self.input_ooi, self.boefje.id))
