import datetime
from typing import List, Optional

from scheduler import models

from ..stores import OOIStorer
from .datastore import SQLAlchemy


class OOIStore(OOIStorer):
    def __init__(self, datastore: SQLAlchemy) -> None:
        super().__init__()

        self.datastore = datastore

    def create_ooi(self, ooi: models.OOI) -> Optional[models.OOI]:
        with self.datastore.session.begin() as session:
            ooi_orm = models.OOIORM(**ooi.dict())
            session.add(ooi_orm)
            return models.OOI.from_orm(ooi_orm)

    def create_or_update_ooi(self, ooi: models.OOI) -> Optional[models.OOI]:
        with self.datastore.session.begin() as session:
            ooi_orm = session.query(models.OOIORM).filter(models.OOIORM.primary_key == ooi.primary_key).first()

            if ooi_orm:
                self.update_ooi(ooi)
                return models.OOI.from_orm(ooi_orm)

            ooi_orm = models.OOIORM(**ooi.dict())
            session.add(ooi_orm)
            return models.OOI.from_orm(ooi_orm)

    def get_ooi(self, ooi_id: str) -> Optional[models.OOI]:
        with self.datastore.session.begin() as session:
            ooi_orm = session.query(models.OOIORM).filter(models.OOIORM.primary_key == ooi_id).first()

            if ooi_orm is None:
                return None

            return models.OOI.from_orm(ooi_orm)

    def update_ooi(self, ooi: models.OOI) -> None:
        with self.datastore.session.begin() as session:
            (session.query(models.OOIORM).filter(models.OOIORM.primary_key == ooi.primary_key).update(ooi.dict()))

    def delete_ooi(self, ooi_id: str) -> None:
        with self.datastore.session.begin() as session:
            (session.query(models.OOIORM).filter(models.OOIORM.primary_key == ooi_id).delete())

    def get_oois_last_checked_since(self, since: datetime.datetime) -> List[models.OOI]:
        with self.datastore.session.begin() as session:
            oois_orm = (
                session.query(models.OOIORM)
                .filter(models.OOIORM.checked_at <= since)
                .order_by(models.OOIORM.checked_at.desc())
                .all()
            )

            return [models.OOI.from_orm(ooi_orm) for ooi_orm in oois_orm]

    def get_oois_by_type(self, organisation_id: str, ooi_type: str) -> List[models.OOI]:
        with self.datastore.session.begin() as session:
            oois_orm = (
                session.query(models.OOIORM)
                .filter(models.OOIORM.organisation_id == organisation_id)
                .filter(models.OOIORM.object_type == ooi_type)
                .all()
            )

            return [models.OOI.from_orm(ooi_orm) for ooi_orm in oois_orm]
