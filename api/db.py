import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_engine: Engine | None = None

def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = os.getenv("DB_URL")
        if not url:
            raise RuntimeError("DB_URL no está definido (.env)")
        _engine = create_engine(url, pool_pre_ping=True, future=True)
    return _engine

@contextmanager
def db_conn():
    with get_engine().connect() as conn:
        yield conn
