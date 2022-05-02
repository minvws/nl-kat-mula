from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ScanProfile(BaseModel):
    reference: Dict[str, Any]
    level: int
    scan_profile_type: str


class OOI(BaseModel):
    """Representation of "Object Of Interests" from Octopoes."""

    primary_key: str
    name: Optional[str]
    ooi_type: str
    scan_profile: Optional[ScanProfile]  # TODO: check if this optional
