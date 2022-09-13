import json
from typing import List, Optional, Tuple, Union

from scheduler import models

from sqlalchemy import create_engine, orm, pool

from ..stores import Datastore, DatastoreType, PriorityQueueStorer, TaskStorer


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
