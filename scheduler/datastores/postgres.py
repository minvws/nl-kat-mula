import json
from typing import List, Union

from scheduler import models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .datastore import Datastore


class PostgreSQL(Datastore):
    def __init__(self, dsn: str="") -> None:
        super().__init__()

        self.engine = create_engine(dsn, pool_pre_ping=True, pool_size=25, json_serializer=lambda obj: json.dumps(obj, default=str))
        self.conn = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)()

    def get_tasks(self, scheduler_id: Union[str, None], status: Union[str, None], offset: int = 0, limit: int = 100) -> (List[models.Task], int):
        query = self.conn.query(models.TaskORM)

        if scheduler_id is not None:
            query = query.filter(models.TaskORM.scheduler_id == scheduler_id)

        if status is not None:
            query = query.filter(models.TaskORM.status == models.TaskStatus(status).name)

        count = query.count()
        tasks_orm = query.offset(offset).limit(limit).all()

        tasks = [models.Task.from_orm(task_orm) for task_orm in tasks_orm]
        return tasks, count

    def get_task_by_id(self, id: str) -> models.Task:
        task_orm = self.conn.query(models.TaskORM).filter(models.TaskORM.id == id).first()
        if task_orm is None:
            return None

        task = models.Task.from_orm(task_orm)

        return task

    def get_task_by_hash(self, hash: str) -> models.Task:
        # task_orm = self.conn.query(models.TaskORM).order_by(models.TaskORM.created_at.desc()).filter(models.TaskORM.hash == hash).first()
        task_orm = self.conn.query(models.TaskORM).filter(models.TaskORM.hash == hash).first()
        if task_orm is None:
            return None

        task = models.Task.from_orm(task_orm)

        return task

    def add_task(self, task: models.Task) -> models.Task:
        task_orm = models.TaskORM(**task.dict())
        self.conn.add(task_orm)
        self.conn.commit()
        self.conn.refresh(task_orm)

        created_task = models.Task.from_orm(task_orm)

        return created_task

    def update_task(self, task: models.Task) -> models.Task:
        task_orm = self.conn.query(models.TaskORM).filter(models.TaskORM.id == task.id).first()
        task_orm.status = task.status
        self.conn.commit()
        self.conn.refresh(task_orm)

        updated_task = models.Task.from_orm(task_orm)

        return updated_task
