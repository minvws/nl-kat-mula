from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from scheduler.models import Base


class Boefje(BaseModel):
    id: str
    name: str
    description: str
    version: Optional[str] = Field(default=None)
    scan_level: int
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

    boefje: Boefje
    input_ooi: str
    arguments: Dict[str, str]
    organization: str

    dispatches: List[Normalizer] = Field(default_factory=list)
