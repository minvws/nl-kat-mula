from typing import Optional

from pydantic import BaseModel


class OOI(BaseModel):
    name: str
    ooi_type: str
    organization: str
    reference: Optional[str]  # FIXME: when endpoint exposes the correct id
