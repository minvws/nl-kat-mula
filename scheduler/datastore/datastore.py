from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class PostgreSQL:
    def __init__(self, dsn=None):
        engine = create_engine(dsn, pool_pre_ping=True, pool_size=25)
        self.conn = sessionmaker(bind=engine)

    def connect(self):
        pass

    def execute(self, *args, **kwargs):
        return self.conn.execute(*args, **kwargs)
