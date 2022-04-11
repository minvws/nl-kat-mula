from pydantic import BaseModel, Field


class Organisation(BaseModel):
    id: str
    name: str
