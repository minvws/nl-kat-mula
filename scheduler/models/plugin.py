from typing import List

from pydantic import BaseModel


class Plugin(BaseModel):
    id: str
    name: str
    version: str
    authors: List[str]
    created: str
    description: str
    environment_keys: List[str]
    related: List[str]
    type: str
    scan_level: int
    consumes: str
    produces: List[str]
    enabled: bool
