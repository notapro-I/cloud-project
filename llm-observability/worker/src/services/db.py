from collections.abc import Iterator
from contextlib import contextmanager

import psycopg2
from psycopg2.extensions import connection

from src.config import settings


@contextmanager
def get_conn() -> Iterator[connection]:
    conn = psycopg2.connect(settings.db_dsn)
    try:
        yield conn
    finally:
        conn.close()
