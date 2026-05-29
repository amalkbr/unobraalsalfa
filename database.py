import psycopg2
from psycopg2.extras import RealDictCursor
import os

def get_conn():
    # أولاً: جرب استخدام DATABASE_URL (الطريقة المفضلة في Railway)
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        return psycopg2.connect(db_url)
    
    # ثانياً: إذا لم يكن موجود، استخدم المتغيرات المنفصلة
    return psycopg2.connect(
        host=os.environ.get('PGHOST'),
        port=os.environ.get('PGPORT'),
        user=os.environ.get('PGUSER'),
        password=os.environ.get('PGPASSWORD'),
        dbname=os.environ.get('PGDATABASE')
    )

def db_query(sql, params=(), commit=False):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(sql, params)
        if commit:
            conn.commit()
            return True
        return cur.fetchall()
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    
    # 1. جدول المستخدمين (تمت إضافة يوزر نيم خاص، باسورد، خصوصية، وحالة الظهور)
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY, 
                    username TEXT, -- يوزر التليجرام العام (اختياري)
                    username_key VARCHAR(50) UNIQUE, -- اليوزر الخاص بالبوت (للبحث والمتابعة)
                    password_key VARCHAR(50), -- رمز حماية الحساب
                    player_name TEXT, 
                    online_points INTEGER DEFAULT 0,
                    is_registered BOOLEAN DEFAULT FALSE,
                    language VARCHAR(2) DEFAULT 'ar',
                    is_private BOOLEAN DEFAULT FALSE, -- هل الحساب خاص؟
                    allow_spectate BOOLEAN DEFAULT TRUE, -- هل يسمح بالمشاهدة؟
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- لخدمة "من متصل الآن"
                )''')
    
    # 2. جدول الغرف (محدث للدومنة وبرا السالفة)
    cur.execute('''CREATE TABLE IF NOT EXISTS rooms (
                    room_id VARCHAR(10) PRIMARY KEY,
                    room_code VARCHAR(10),
                    creator_id BIGINT,
                    host_id BIGINT,
                    max_players INT,
                    win_limit INT DEFAULT 101,
                    status VARCHAR(20) DEFAULT 'waiting',
                    game_type VARCHAR(20) DEFAULT 'domino',
                    game_data JSONB DEFAULT '{}'::jsonb,
                    is_random BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 3. جدول اللاعبين داخل الغرفة
    cur.execute('''CREATE TABLE IF NOT EXISTS room_players (
                    room_id VARCHAR(10),
                    room_code VARCHAR(10),
                    user_id BIGINT,
                    player_name VARCHAR(100),
                    points INT DEFAULT 0,
                    team VARCHAR(10) DEFAULT '0',
                    is_ready BOOLEAN DEFAULT FALSE,
                    join_order INTEGER DEFAULT 0,
                    last_msg_id BIGINT,
                    PRIMARY KEY (room_id, user_id))''')

    # 4. جدول المتابعات
    cur.execute('''CREATE TABLE IF NOT EXISTS follows (
                    follower_id BIGINT, 
                    following_id BIGINT, 
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (follower_id, following_id))''')

    # 5. جدول الإسكات
    cur.execute('''CREATE TABLE IF NOT EXISTS mutes (
                    sender_id BIGINT, 
                    receiver_id BIGINT, 
                    expire_at TIMESTAMP, 
                    PRIMARY KEY (sender_id, receiver_id))''')

    # تحديثات إجبارية
    alter_queries = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS username_key VARCHAR(50) UNIQUE;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_key VARCHAR(50);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_private BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS allow_spectate BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(2) DEFAULT 'ar';",
        "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS room_code VARCHAR(10);",
        "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS host_id BIGINT;",
        "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS win_limit INT DEFAULT 101;",
        "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS game_type VARCHAR(20) DEFAULT 'domino';",
        "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS game_data JSONB DEFAULT '{}'::jsonb;",
        "ALTER TABLE room_players ADD COLUMN IF NOT EXISTS room_code VARCHAR(10);",
        "ALTER TABLE room_players ADD COLUMN IF NOT EXISTS team VARCHAR(10) DEFAULT '0';"
    ]

    for query in alter_queries:
        try:
            cur.execute(query)
        except Exception as e:
            print(f"⚠️ Warning during alter: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database initialized with social features successfully!")
