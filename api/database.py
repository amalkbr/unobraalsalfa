import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_conn():
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        try:
            # استخدام sslmode='require' للاتصال بـ Vercel/Railway
            conn = psycopg2.connect(db_url, sslmode='require')
            return conn
        except Exception as e:
            print(f"DB Error: {e}")
            return None
    return None
