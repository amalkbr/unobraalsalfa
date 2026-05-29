import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')

# Initialize connection pool
# minconn=1, maxconn=20 (adjust based on your database plan limits)
try:
    if DATABASE_URL:
        pool = ThreadedConnectionPool(1, 20, DATABASE_URL, sslmode='require')
    else:
        pool = None
except Exception as e:
    print(f"Error initializing DB pool: {e}")
    pool = None

@contextmanager
def get_db():
    if pool is None:
        yield None
        return

    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)

def get_db_conn():
    """Legacy support for direct connection access, but get_db() context manager is preferred."""
    if pool:
        return pool.getconn()
    return None

def release_db_conn(conn):
    """Legacy support to release a connection back to the pool."""
    if pool and conn:
        pool.putconn(conn)
