import json
from typing import List, Optional, Tuple, Union

from scheduler import models

from sqlalchemy import create_engine, orm, pool

from ..stores import PriorityQueueStorer
from .datastore import SQLAlchemy


class PriorityQueueStore(PriorityQueueStorer):
    def __init__(self, datastore: SQLAlchemy) -> None:
        super().__init__()

        self.datastore = datastore

    def pop(self, scheduler_id: str) -> Optional[models.Task]:
        with self.datastore.session.begin() as session:
            item_orm = (
                session.query(models.PrioritizedItemORM)
                .filter(models.PrioritizedItemORM.scheduler_id == scheduler_id)
                .order_by(models.PrioritizedItemORM.priority.asc())
                .order_by(models.PrioritizedItemORM.created_at.asc())
                .first()
            )

            if item_orm is None:
                return None

            return models.PrioritizedItem.from_orm(item_orm)

    def push(self, scheduler_id: str, item: models.PrioritizedItem) -> Optional[models.PrioritizedItem]:
        with self.datastore.session.begin() as session:
            item_orm = models.PrioritizedItemORM(**item.dict())
            session.add(item_orm)

            return models.PrioritizedItem.from_orm(item_orm)

    def peek(self, scheduler_id: str, index: str) -> Optional[models.PrioritizedItem]:
        with self.datastore.session.begin() as session:
            item_orm = (
                session.query(models.PrioritizedItem)
                .filter(models.PrioritizedItemORM.scheduler_id == scheduler_id)
                .order_by(models.PrioritizedItemORM.priority.asc())
                .order_by(models.PrioritizedItemORM.created_at.asc())
                .offset(index)
                .first()
            )

            if item_orm is None:
                return None

            return models.PrioritizedItem.from_orm(item_orm)

    def update(self, item: models.PrioritizedItem) -> Optional[models.PrioritizedItem]:
        with self.datastore.session.begin() as session:
            task_orm = (
                session.query(models.PrioritizedItemORM)
                .filter(models.PrioritizedItem == item.id)
                .one_or_none()
            )
            if task_orm is None:
                return None

            update_data = item.dict(exclude_unset=True)
            updated_item = item_orm.copy(update=update_data)

            return models.PrioritizedItem.from_orm(updated_item)

    def remove(self, scheduler_id: str, item_id: str) -> None:
        with self.datastore.session.begin() as session:
            item_orm = session.query(models.PrioritizedItemORM).get(item_id)
            session.delete(item_orm)

    def empty(self, scheduler_id: str) -> bool:
        with self.datastore.session.begin() as session:
            count = (
                session.query(models.PrioritizedItemORM)
                .filter(models.PrioritizedItemORM.scheduler_id == scheduler_id)
                .count()
            )
            return count == 0

    def qsize(self, scheduler_id: str) -> int:
        with self.datastore.session.begin() as session:
            count = (
                session.query(models.PrioritizedItemORM)
                .filter(models.PrioritizedItemORM.scheduler_id == scheduler_id)
                .count()
            )

            return count

    def search(self, scheduler_id: str) -> List[models.Task]:
        pass

    def get_item_by_hash(self, scheduler_id: str, item_hash: str) -> Optional[models.PrioritizedItem]:
        with self.datastore.session.begin() as session:
            item_orm = (
                session.query(models.PrioritizedItemORM)
                .order_by(models.PrioritizedItemORM.created_at.desc())
                .filter(models.PrioritizedItemORM.scheduler_id == scheduler_id)
                .filter(models.PrioritizedItemORM.hash == item_hash)
                .first()
            )

            if item_orm is None:
                return None

            return models.PrioritizedItem.from_orm(item_orm)

    def get_items_by_scheduler_id(self, scheduler_id: str) -> List[models.PrioritizedItem]:
        with self.datastore.session.begin() as session:
            items_orm = (
                session.query(models.PrioritizedItemORM)
                .filter(models.PrioritizedItemORM.scheduler_id == scheduler_id)
                .all()
            )

            return [models.PrioritizedItem.from_orm(item_orm) for item_orm in items_orm]
