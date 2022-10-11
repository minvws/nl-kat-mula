import json
from typing import List, Optional, Tuple, Union

from scheduler import models

from sqlalchemy import create_engine, orm, pool

from ..stores import Datastore, DatastoreType, PriorityQueueStorer, TaskStorer


class SQLAlchemy(Datastore):
    """SQLAlchemy datastore implementation

    Note on using sqlite:

    By default SQLite will only allow one thread to communicate with it,
    assuming that each thread would handle an independent request. This is to
    prevent accidentally sharing the same connection for different things (for
    different requests). But within the scheduler more than one thread could
    interact with the database. So we need to make SQLite know that it should
    allow that with

    Also, we will make sure each request gets its own database connection
    session.

    See: https://docs.sqlalchemy.org/en/14/dialects/sqlite.html#using-a-memory-database-in-multiple-threads
    """

    def __init__(self, dsn: str, datastore_type: DatastoreType) -> None:
        super().__init__()

        self.engine = None

        if dsn.startswith("sqlite"):
            self.engine = create_engine(
                dsn,
                connect_args={"check_same_thread": False},
                poolclass=pool.StaticPool,
                json_serializer=lambda obj: json.dumps(obj, default=str),
            )
        else:
            self.engine = create_engine(
                dsn,
                pool_pre_ping=True,
                pool_size=25,
                json_serializer=lambda obj: json.dumps(obj, default=str),
            )

        if self.engine is None:
            raise Exception("Invalid datastore type")

        models.Base.metadata.create_all(self.engine)

        self.session = orm.sessionmaker(
            bind=self.engine,
        )
