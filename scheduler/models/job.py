from pydantic import BaseModel
from sqlalchemy import Column, Integer


class JobORM(Base):
    """Database model for the jobs table."""

    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, nullable=False)


# TODO: necessary to be persisted in the database?
class Job(BaseModel):
    """Representation of a job on the priority queue."""

    id: int

    class Config:
        orm_mode = True
