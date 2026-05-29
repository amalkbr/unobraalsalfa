import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager

# الحصول على رابط قاعدة البيانات من المتغيرات البيئية
DATABASE_URL = os.environ.get('DATABASE_URL')

# تهيئة تجمع الاتصالات (Connection Pool)
# نستخدم ThreadedConnectionPool لدعم التعددية (Concurrency) بشكل أفضل
try:
    if DATABASE_URL:
        # نقوم بضبط minconn=2 و maxconn=20 لضمان وجود اتصالات جاهزة دائماً
        pool = ThreadedConnectionPool(2, 20, DATABASE_URL, sslmode='require')
    else:
        pool = None
except Exception as e:
    print(f"Error initializing DB pool: {e}")
    pool = None

@contextmanager
def get_db():
    """
    مدير سياق (Context Manager) للحصول على اتصال من الـ Pool.
    يضمن إعادة الاتصال للـ Pool تلقائياً حتى في حال حدوث خطأ.
    """
    if pool is None:
        yield None
        return

    conn = pool.getconn()
    try:
        # نغلق autocommit لضمان التحكم اليدوي بالـ transactions ومنع الـ Deadlocks
        conn.autocommit = False
        yield conn
    except Exception as e:
        if conn:
            conn.rollback() # التراجع في حال حدوث خطأ
        raise e
    finally:
        if pool and conn:
            pool.putconn(conn) # إعادة الاتصال للمستودع بدلاً من إغلاقه

def get_db_conn():
    """دعم للوظائف القديمة، يفضل استخدام get_db() بدلاً منها."""
    if pool:
        return pool.getconn()
    return None

def release_db_conn(conn):
    """إعادة الاتصال يدوياً، يفضل استخدام get_db()."""
    if pool and conn:
        pool.putconn(conn)
