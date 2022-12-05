import datetime
from typing import Dict

import mmh3
from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, DateTime, Integer, String

from .base import Base


class ScheduledObject(BaseModel):

    hash = str
    type = str
    data = Dict

    checked_at: Optional[datetime.datetime] = Field(default=None)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    modified_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    class Config:
        orm_mode = True


class ScheduledObjectORM(Base):

    __tablename__ = "tracked_objects"

    hash = Column(String, primary_key=True)
    type = Column(String)
    data = Column(JSON)
    organisation_id = Column(String)

    # Should allow nullable, because when null it didn't get checked
    checked_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    modified_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.datetime.utcnow,
    )
