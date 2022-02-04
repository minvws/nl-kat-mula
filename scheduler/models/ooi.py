from pydantic import BaseModel
from scheduler.models import Base
from sqlalchemy import Column, Integer


class OOIORM(Base):
    __tablename__ = "ooi"

    id = Column(Integer, primary_key=True, nullable=False)


class OOI(BaseModel):
    id: int

    class Config:
        orm_mode = True
