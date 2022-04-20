from typing import Optional

from pydantic import BaseModel, Field


class ScanProfile(BaseModel):
    reference: str
    level: int
    scan_profile_type: str


class OOI(BaseModel):
    """Representation of "Object Of Interests" from Octopoes."""

    id: str = Field(..., alias="__id__")
    name: Optional[str]
    ooi_type: str
    scan_profile: Optional[ScanProfile]
