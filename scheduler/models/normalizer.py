from typing import Optional

from pydantic import BaseModel, Field


class Normalizer(BaseModel):
    id: str
    name: str
    version: Optional[str] = Field(default=None)


# TODO: not yet correct
class NormalizerTask(BaseModel):
    """NormalizerTask represent data needed for a Normalizer to run."""

    id: str
    normalizer: Normalizer
    input_ooi: str
    organization: str

    def __hash__(self) -> int:
        """Make NormalizerTask hashable, so that we can deduplicate it when used
        in the PriorityQueue. We hash the combination of the attributes
        input_ooi and normalizer.id since this combination is unique."""
        return hash((self.input_ooi, self.normalizer.id, self.organization))
