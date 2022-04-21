from typing import Optional

from pydantic import BaseModel, Field


class OOI(BaseModel):
    """Representation of "Object Of Interests" from Octopoes."""

    id: str = Field(..., alias="__id__")
    name: Optional[str]
    ooi_type: str
    # organization: str
