from typing import Optional

from pydantic import BaseModel, Field

from .scan_profile import ScanProfile


class OOI(BaseModel):
    """Representation of "Object Of Interests" from Octopoes."""

    primary_key: str
    name: Optional[str]
    ooi_type: str
    scan_profile: Optional[ScanProfile]  # TODO: check if this optional
