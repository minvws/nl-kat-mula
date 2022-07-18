import json

from scheduler import models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .datastore import Datastore


class PostgreSQL(Datastore):
    def __init__(self, dsn: str="") -> None:
        super().__init__()

        self.engine = create_engine(dsn, pool_pre_ping=True, pool_size=25, json_serializer=lambda obj: json.dumps(obj, default=str))
        self.conn = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)()

    def get_task_by_id(self, task_id: str) -> models.Task:
        task_orm = self.conn.query(models.TaskORM).filter(models.TaskORM.id == task_id).first()
        if task_orm is None:
            return None

        task = models.Task.from_orm(task_orm)
        return task

    def add_task(self, task: models.Task) -> models.Task:
        task_orm = models.TaskORM(**task.dict())
        self.conn.add(task_orm)
        self.conn.commit()
        self.conn.refresh(task_orm)

        self.logger.debug(f"Added task {task_orm.__dict__}")

        created_task = models.Task.from_orm(task_orm)
        return created_task

    def update_task(self, task: models.Task) -> models.Task:
        task_orm = self.conn.query(models.TaskORM).filter(models.TaskORM.id == task.id).first()
        task_orm.status = task.status
        self.conn.commit()
        self.conn.refresh(task_orm)

        self.logger.debug(f"Updated task {task_orm.__dict__}")

        updated_task = models.Task.from_orm(task_orm)
        return updated_task
