from typing import Optional

from pydantic import BaseModel


class OOI(BaseModel):
    """Representation of "Object Of Interests"" from Octopoes.
    """
    name: str
    ooi_type: str
    organization: str
    reference: Optional[str]  # FIXME: when endpoint exposes the correct id
