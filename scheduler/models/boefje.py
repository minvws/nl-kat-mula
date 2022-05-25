from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from .normalizer import Normalizer


class Boefje(BaseModel):
    """Boefje representation."""

    id: str
    name: Optional[str]
    description: Optional[str]
    version: Optional[str] = Field(default=None)
    scan_level: Optional[int] = Field(default=None)
    consumes: Optional[Union[str, List[str]]
    produces: Optional[List[str]]
    dispatches: Optional[Dict[str, List[str]]] = Field(default=None)


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


class BoefjeMeta(BaseModel):
    """BoefjeMeta is the response object returned by the Bytes API"""

    id: str
    boefje: Boefje
    input_ooi: str
    arguments: Dict[str, Any]
    organization: str
    started_at: datetime
    ended_at: datetime
