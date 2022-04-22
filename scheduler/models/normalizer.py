from typing import Optional

from pydantic import BaseModel, Field


class Normalizer(BaseModel):
    id: str
    name: str
    version: Optional[str] = Field(default=None)
