import datetime
from typing import Optional

import mmh3
from pydantic import BaseModel
from sqlalchemy import JSON, Column, DateTime, Enum, String

from .base import Base
from .scan_profile import ScanProfile


class OOI(BaseModel):
    """Representation of "Object Of Interests" from Octopoes."""

    primary_key: str
    object_type: str
    scan_profile: ScanProfile
    organisation_id: Optional[str]

    checked_at: Optional[datetime.datetime]
    created_at: Optional[datetime.datetime]
    modified_at: Optional[datetime.datetime]

    class Config:
        orm_mode = True

    def __hash__(self):
        return hash((self.primary_key, self.organisation_id))


class OOIORM(Base):
    """A SQLAlchemy datastore model respresentation of an OOI, this is
    specifically done for BoefjeSchedulers to keep track of the OOI's
    that have been and are being scanned.
    """
    __tablename__ = "oois"

    primary_key = Column(String, primary_key=True)
    object_type = Column(String)
    scan_profile = Column(JSON)
    organisation_id = Column(String)

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
