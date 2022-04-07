"""
Reference implementation for potential PostgreSQL database connections.
at the moment this isn't used.

"""
from typing import Any, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class PostgreSQL:
    def __init__(self, dsn: str = ""):
        engine = create_engine(dsn, pool_pre_ping=True, pool_size=25)
        self.conn = sessionmaker(bind=engine)

    def connect(self) -> None:
        pass

    def execute(self) -> None:
        pass
