from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from scheduler.models import Base

from .normalizer import Normalizer


class Boefje(BaseModel):
    """Boefje representation."""

    id: str
    name: str
    description: str
    version: Optional[str] = Field(default=None)
    scan_level: Optional[int] = Field(default=None)
    consumes: List[str]
    produces: List[str]
    dispatches: Optional[Dict[str, List[str]]] = Field(default=None)


class BoefjeTask(BaseModel):
    """BoefjeTask represent data needed for a Boefje to run."""

    # id: str
    boefje: Boefje
    input_ooi: str
    organization: str

    dispatches: List[Normalizer] = Field(default_factory=list)

    def __hash__(self) -> int:
        """Make BoefjeTask hashable, so that we can de-duplicate it when used
        in the PriorityQueue. We hash the combination of the attributes
        input_ooi and boefje.id since this combination is unique."""
        return hash((self.input_ooi, self.boefje.id, self.organization))
