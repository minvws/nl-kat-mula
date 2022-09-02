import json
from typing import List, Optional, Tuple, Union

from scheduler import models

from sqlalchemy import create_engine, orm, pool

from .datastore import (Datastore, DatastoreType, PriorityQueueStorer,
                        TaskStorer)


class SQLAlchemy(Datastore):
    def __init__(self, dsn: str, datastore_type: DatastoreType) -> None:
        super().__init__()

        self.engine = None

        if datastore_type == DatastoreType.POSTGRES:
            self.engine = create_engine(
                dsn,
                pool_pre_ping=True,
                pool_size=25,
                json_serializer=lambda obj: json.dumps(obj, default=str),
            )
        elif datastore_type == DatastoreType.SQLITE:
            # See: https://docs.sqlalchemy.org/en/14/dialects/sqlite.html#using-a-memory-database-in-multiple-threads
            self.engine = create_engine(
                dsn,
                connect_args={"check_same_thread": False},
                poolclass=pool.StaticPool,
                json_serializer=lambda obj: json.dumps(obj, default=str),
            )

        if self.engine is None:
            raise Exception("Invalid datastore type")

        models.Base.metadata.create_all(self.engine)

        self.session = orm.sessionmaker(
            bind=self.engine,
        )


class TaskStore(TaskStorer):
    def __init__(self, datastore: SQLAlchemy) -> None:
        super().__init__()

        self.datastore = datastore

    def get_tasks(
        self, scheduler_id: Union[str, None], status: Union[str, None], offset: int = 0, limit: int = 100
    ) -> Tuple[List[models.Task], int]:
        with self.datastore.session.begin() as session:
            query = session.query(models.TaskORM)

            if scheduler_id is not None:
                query = query.filter(models.TaskORM.scheduler_id == scheduler_id)

            if status is not None:
                query = query.filter(models.TaskORM.status == models.TaskStatus(status).name)

            count = query.count()
            tasks_orm = query.order_by(models.TaskORM.created_at.desc()).offset(offset).limit(limit).all()

            tasks = [models.Task.from_orm(task_orm) for task_orm in tasks_orm]

        return tasks, count

    def get_task_by_id(self, task_id: str) -> Optional[models.Task]:
        with self.datastore.session.begin() as session:
            task_orm = session.query(models.TaskORM).filter(models.TaskORM.id == task_id).first()
            if task_orm is None:
                return None

            task = models.Task.from_orm(task_orm)

        return task

    def get_task_by_hash(self, task_hash: str) -> Optional[models.Task]:
        with self.datastore.session.begin() as session:
            task_orm = (
                session.query(models.TaskORM)
                .order_by(models.TaskORM.created_at.desc())
                .filter(models.TaskORM.hash == task_hash)
                .first()
            )

            if task_orm is None:
                return None

            task = models.Task.from_orm(task_orm)

        return task

    def add_task(self, task: models.Task) -> Optional[models.Task]:
        with self.datastore.session.begin() as session:
            task_orm = models.TaskORM(**task.dict())
            session.add(task_orm)

            created_task = models.Task.from_orm(task_orm)

        return created_task

    def update_task(self, task: models.Task) -> Optional[models.Task]:
        with self.datastore.session.begin() as session:
            task_orm = session.query(models.TaskORM).get(task.id)
            task_orm.status = task.status

            updated_task = models.Task.from_orm(task_orm)

        return updated_task


class PriorityQueueStore(PriorityQueueStorer):
    def __init__(self, datastore: SQLAlchemy) -> None:
        super().__init__()
        self.datastore = datastore

    def push(self, scheduler_id: str, task: models.Task) -> None:
        pass

    def pop(self, scheduler_id: str) -> Optional[models.Task]:
        with self.datastore.session.begin() as session:
            task_orm = (
                session.query(models.TaskORM)
                .filter(models.TaskORM.scheduler_id == scheduler_id)
                .order_by(models.TaskORM.priority.asc())
                .order_by(models.TaskORM.created_at.asc())
                .first()
            )

            if task_orm is None:
                return None

            return models.Task.from_orm(task_orm)

    def peek(self, scheduler_id: str) -> Optional[models.Task]:
        pass

    def remove(self, scheduler_id: str) -> None:
        pass

    def empty(self, scheduler_id: str) -> bool:
        pass

    def qsize(self, scheduler_id: str) -> int:
        with self.datastore.session.begin() as session:
            count = session.query(models.TaskORM).filter(models.TaskORM.scheduler_id == scheduler_id).count()
            return count

    def search(self, scheduler_id: str) -> List[models.Task]:
        pass

    def get_task_by_hash(self, pq_id: str, task_hash: str) -> Optional[models.Task]:
        with self.datastore.session.begin() as session:
            task_orm = (
                session.query(models.TaskORM)
                .order_by(models.TaskORM.created_at.desc())
                .filter(models.TaskORM.scheduler_id == pq_id)
                .filter(models.TaskORM.hash == task_hash)
                .first()
            )

            if task_orm is None:
                return None

            task = models.Task.from_orm(task_orm)

        return task
