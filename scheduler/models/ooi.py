import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import JSON, Column, DateTime, Enum, String

from .base import Base
from .scan_profile import ScanProfile


class OOI(BaseModel):
    """Representation of "Object Of Interests" from Octopoes."""

    primary_key: str
    object_type: str
    scan_profile: ScanProfile

    class Config:
        orm_mode = True


class OOIORM(Base):
    """A SQLAlchemy datastore model respresentation of an OOI, this is
    specifically done for BoefjeSchedulers to keep track of the OOI's
    that have been and are being scanned.
    """
    __tablename__ = "oois"

    primary_key = Column(String, primary_key=True)
    name = Column(String)
    ooi_type = Column(String)
    object_type = Column(String)

    scan_profile = Column(JSON)

    checked_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.datetime.utcnow,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.datetime.utcnow,
    )

    modified_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
