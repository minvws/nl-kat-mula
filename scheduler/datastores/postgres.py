from scheduler import models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .datastore import Datastore


class PostgreSQL(Datastore):
    def __init__(self, dsn: str="") -> None:
        engine = create_engine(dsn, pool_pre_ping=True, pool_size=25)
        self.conn = sessionmaker(bind=engine)

    def connect(self) -> None:
        pass

    def execute(self) -> None:
        pass

    def add_task(self, task: models.Task) -> None:
        task_orm = models.TaskORM(
            task_id=p_item.item.task_id,
            task_type=p_item.item.task_type,
            task_status=models.TaskStatus.PENDING,
            task_priority=p_item.item.task_priority,
            task_rank=p_item.item.task_rank,
            task_data=p_item.item.task_data,
            task_scheduler_id=self.scheduler_id,
            task_scheduler_type=self.__class__.__name__,
            task_scheduler_data=self.dict(),
        )
        self.conn.add(task_orm)
        self.conn.commit()
