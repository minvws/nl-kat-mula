from pydantic import BaseModel
from sqlalchemy import Column, Integer


class JobORM(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, nullable=False)


class Job(BaseModel):
    id: int

    class Config:
        orm_mode = True
