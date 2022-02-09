from pydantic import BaseModel
from scheduler.models import Base
from sqlalchemy import Column, Integer, String


class OOIDB(Base):
    __tablename__ = "ooi"

    id = Column(Integer, primary_key=True, nullable=False)
    reference = Column(String(255), nullable=False)


class OOI(BaseModel):
    reference: str

    class Config:
        orm_mode = True
