from scheduler import models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .datastore import Datastore


class PostgreSQL(Datastore):
    def __init__(self, dsn: str="") -> None:
        super().__init__()

        engine = create_engine(dsn, pool_pre_ping=True, pool_size=25)
        self.conn = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    # TODO: json serialization on datetime from normalizer task doesn't work
    def add_task(self, task: models.Task) -> models.Task:
        task_orm = models.TaskORM(**task.dict())
        self.conn.add(task_orm)
        self.conn.commit()
        self.conn.refresh(task_orm)

        self.logger.debug(f"Added task {task_orm.__dict__}")

        created_task = models.Task.from_orm(task_orm)
        return created_task
