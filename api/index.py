from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import json
import random
import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

# --- Database Connection ---
DB_INITIALIZED = False

def get_db_conn():
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        try:
            conn = psycopg2.connect(db_url, sslmode='require')
            return conn
        except Exception as e:
            print(f"DB Error: {e}")
            return None
    return None

CATEGORIES = {
    "أكلات": ["بيتزا", "برجر", "شاورما", "منسف", "كبسة", "فلافل", "مندي", "باستا", "دولمة", "برياني", "مسحب", "كبة", "بخاري", "مقلوبة", "سوشي", "تاكو", "ملوخية", "باشميل"],
    "حيوانات": ["أسد", "نمر", "زرافة", "فيل", "قطة", "كلب", "أرنب", "قرد", "تمساح", "ثعلب", "ذئب", "جمل", "حصان", "سنجاب", "بطريق", "دولفين", "قرش"],
    "ملابس": ["قميص", "بنطلون", "فستان", "تنورة", "جاكيت", "قبعة", "جوارب", "حذاء", "ربطة عنق", "بلوزة", "بشت", "شماغ", "عباية", "هودي"],
    "كورة": ["ريال مدريد", "برشلونة", "ليفربول", "الهلال", "النصر", "الاتحاد", "الاهلي", "ميسي", "رونالدو", "صلاح", "مبابي", "نيمار", "مانشستر سيتي", "بايرن ميونخ"],
    "سيارات": ["تويوتا", "مرسيدس", "فورد", "تسلا", "نيسان", "هوندا", "بي ام دبليو", "لكزس", "مازدا", "كيا", "باجيرو", "لاند كروزر", "شفروليه", "كامري", "بنتلي"],
    "شركات": ["جوجل", "ابل", "مايكروسوفت", "سامسونج", "امازون", "فيسبوك", "تسلا", "كوكاكولا", "بيبسي", "نايكي", "اديداس", "هواوي", "سوني"],
    "كواكب": ["المريخ", "المشتري", "زحل", "الأرض", "الزهرة", "عطارد", "نبتون", "أورانوس", "الشمس", "القمر", "بلوتو"],
    "أجهزة": ["آيفون", "بليستيشن", "لابتوب", "تلفزيون", "ساعة ذكية", "كاميرا", "ايباد", "اكس بوكس", "بي سي", "سماعات", "غسالة", "مكيف", "ثلاجة", "مايكرويف"],
    "تطبيقات": ["واتساب", "انستقرام", "تيك توك", "سناب شات", "تلغرام", "يوتيوب", "تويتر", "فيسبوك", "ديسكورد", "سبوتيفاي", "نتفلكس", "بوجي"],
    "فواكه وخضار": ["تفاح", "موز", "مانجو", "فراولة", "بطيخ", "عنب", "برتقال", "أناناس", "كيوي", "توت", "كرز", "رمان", "خيار", "طماطم", "جزر", "بطاطس", "بصل"],
    "شخصيات": ["سوبرمان", "باتمان", "سبايدرمان", "جوكر", "هالك", "ايرون مان", "ثور", "كابتن امريكا", "ثانوس", "بلاك بانثر"],
    "كارتون": ["توم وجيري", "ميكي ماوس", "سبونج بوب", "بن 10", "غامبول", "سبيستون", "سابق ولاحق", "كونان", "بوكيمون", "سندباد"],
    "مشروبات": ["شاي", "قهوة", "عصير", "حليب", "بيبسي", "كوكاكولا", "ميرندا", "سفن اب", "كود رد", "بايسن", "موخيتو", "كركديه"],
    "حلويات": ["كنافة", "بسبوسة", "بقلاوة", "دونات", "تشيز كيك", "كيك", "كريب", "وافل", "ايس كريم", "ماكرون", "سينابون"],
    "مسلسلات": ["صراع العروش", "لا كاسا دي بابل", "بريكنج باد", "فريندز", "الموتى السائرون", "بيكي بلايندرز", "سكيد جيم", "رشاش"],
    "انمي": ["ون بيس", "ناروتو", "هجوم العمالقة", "دراجون بول", "هنتر", "بليتش", "كونان", "ديمون سلاير", "جوجوتسو", "ديث نوت"],
    "كيبوب": ["بي تي اس", "بلاك بينك", "اكسو", "توايس", "ستراي كيدز", "ريد فيلفيت", "ايتيز", "نيوجينز"],
    "قيمرز": ["نينجا", "بندريتا", "ابو فلة", "تي ام فيصل", "باور", "سيد", "اوشي", "شراود", "ميث"],
    "مهن": ["طيار", "دكتور", "مهندس", "طباخ", "شرطي", "رائد فضاء", "معلم", "لاعب كرة", "مبرمج", "حلاق"]
}

def init_db():
    global DB_INITIALIZED
    if DB_INITIALIZED: return
    conn = get_db_conn()
    if not conn: return
    try:
        with conn.cursor() as cur:
            # 1. الأساسيات: جداول المستخدمين والغرف واللاعبين
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username_key TEXT UNIQUE,
                    password_key TEXT,
                    player_name TEXT,
                    is_registered BOOLEAN DEFAULT FALSE,
                    total_wins INTEGER DEFAULT 0,
                    online_points INTEGER DEFAULT 0,
                    saved_players JSONB DEFAULT '[]'
                );
                CREATE TABLE IF NOT EXISTS rooms (
                    room_code TEXT PRIMARY KEY,
                    host_id BIGINT,
                    status TEXT DEFAULT 'waiting',
                    category TEXT,
                    win_limit INTEGER DEFAULT 5,
                    current_turn_asker BIGINT,
                    current_turn_answerer BIGINT,
                    secret_word TEXT,
                    spy_id BIGINT,
                    game_data JSONB DEFAULT '{}',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS room_players (
                    room_code TEXT,
                    user_id BIGINT,
                    player_name TEXT,
                    score INTEGER DEFAULT 0,
                    is_ready BOOLEAN DEFAULT FALSE,
                    yellow_cards INTEGER DEFAULT 0,
                    red_card BOOLEAN DEFAULT FALSE,
                    vote_limit INTEGER,
                    vote_cat TEXT,
                    join_order INTEGER DEFAULT 0,
                    PRIMARY KEY (room_code, user_id)
                );
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE,
                    image_url TEXT,
                    display_order INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS words (
                    id SERIAL PRIMARY KEY,
                    category TEXT,
                    word TEXT
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            """)

            # 2. هجرة البيانات وتوافق الأعمدة (Migrations)
            # تنفيذ العمليات خطوة بخطوة لضمان استمرار التشغيل حتى لو فشلت إحدى الخطوات
            migration_steps = [
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS total_wins INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS online_points INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS saved_players JSONB DEFAULT '[]'",
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS room_code TEXT",
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS room_id TEXT",
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS host_id BIGINT",
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS creator_id BIGINT",
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS category TEXT",
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS win_limit INTEGER DEFAULT 5",
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS current_turn_asker BIGINT",
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS current_turn_answerer BIGINT",
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS secret_word TEXT",
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS spy_id BIGINT",
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS game_data JSONB DEFAULT '{}'::jsonb",
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "ALTER TABLE room_players ADD COLUMN IF NOT EXISTS room_code TEXT",
                "ALTER TABLE room_players ADD COLUMN IF NOT EXISTS room_id TEXT",
                "ALTER TABLE room_players ADD COLUMN IF NOT EXISTS join_order INTEGER DEFAULT 0",
                "ALTER TABLE room_players ADD COLUMN IF NOT EXISTS score INTEGER DEFAULT 0",
                "ALTER TABLE room_players ADD COLUMN IF NOT EXISTS yellow_cards INTEGER DEFAULT 0",
                "ALTER TABLE room_players ADD COLUMN IF NOT EXISTS red_card BOOLEAN DEFAULT FALSE",
                "ALTER TABLE room_players ADD COLUMN IF NOT EXISTS vote_limit INTEGER",
                "ALTER TABLE room_players ADD COLUMN IF NOT EXISTS vote_cat TEXT",
                # محاولة تحويل الأنواع لدعم التوافق باستخدام USING لضمان التحويل الصحيح
                "ALTER TABLE rooms ALTER COLUMN room_id TYPE TEXT USING room_id::TEXT",
                "ALTER TABLE rooms ALTER COLUMN room_code TYPE TEXT USING room_code::TEXT",
                "ALTER TABLE room_players ALTER COLUMN room_id TYPE TEXT USING room_id::TEXT",
                "ALTER TABLE room_players ALTER COLUMN room_code TYPE TEXT USING room_code::TEXT",
                # مزامنة البيانات بين الأعمدة المتقابلة
                "UPDATE rooms SET room_code = room_id WHERE room_code IS NULL AND room_id IS NOT NULL",
                "UPDATE rooms SET room_id = room_code WHERE room_id IS NULL AND room_code IS NOT NULL",
                "UPDATE rooms SET host_id = creator_id WHERE host_id IS NULL AND creator_id IS NOT NULL",
                "UPDATE rooms SET creator_id = host_id WHERE creator_id IS NULL AND host_id IS NOT NULL",
                "UPDATE room_players SET room_code = room_id WHERE room_code IS NULL AND room_id IS NOT NULL",
                "UPDATE room_players SET room_id = room_code WHERE room_id IS NULL AND room_code IS NOT NULL",
                # ضمان وجود الفهارس الضرورية
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_rooms_room_code ON rooms(room_code)",
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_room_players_code_user ON room_players(room_code, user_id)"
            ]

            for step in migration_steps:
                try:
                    cur.execute(step)
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    # طباعة الخطأ في سجلات الخادم للمساعدة في التشخيص
                    print(f"Migration Step Info: {step} | Result: {e}")

            # 3. إعدادات افتراضية
            cur.execute("""
                INSERT INTO settings (key, value) VALUES ('question_timeout', '30') ON CONFLICT DO NOTHING;
                INSERT INTO settings (key, value) VALUES ('vote_timeout', '10') ON CONFLICT DO NOTHING;
                INSERT INTO settings (key, value) VALUES ('spy_guess_timeout', '15') ON CONFLICT DO NOTHING;
                INSERT INTO settings (key, value) VALUES ('sound_click', '') ON CONFLICT (key) DO UPDATE SET value = '' WHERE settings.value LIKE '%soundjay.com%';
            """)

            # --- Seeding Data ---
            cur.execute("SELECT EXISTS (SELECT 1 FROM words LIMIT 1)")
            if not cur.fetchone()[0]:
                for cat, word_list in CATEGORIES.items():
                    cur.execute("INSERT INTO categories (name) VALUES (%s) ON CONFLICT DO NOTHING", (cat,))
                    for word in word_list:
                        cur.execute("INSERT INTO words (category, word) VALUES (%s, %s)", (cat, word.strip()))

            conn.commit()
            DB_INITIALIZED = True
    except Exception as e:
        print(f"Database initialization failed: {e}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
async def home(): return HTML_TEMPLATE

@app.get("/manifest.json")
async def manifest():
    return FileResponse(os.path.join("static", "manifest.json"))

@app.get("/sw.js")
async def service_worker():
    return FileResponse(os.path.join("static", "sw.js"))

@app.get("/join/{room_code}", response_class=HTMLResponse)
async def join_room_link(room_code: str):
    return HTML_TEMPLATE

@app.get("/api/settings")
async def get_settings():
    conn = get_db_conn()
    defaults = {
        "question_timeout": 30,
        "vote_timeout": 10,
        "spy_guess_timeout": 15,
        "sound_click": "",
        "sound_reveal": "",
        "sound_win": "",
        "sound_fail": ""
    }
    if not conn: return defaults
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT key, value FROM settings")
            rows = cur.fetchall()
            settings = {row[0]: row[1] for row in rows}

            # Merge with defaults
            for k, v in defaults.items():
                if k not in settings:
                    settings[k] = v
                elif k.endswith('_timeout'):
                    try: settings[k] = int(settings[k])
                    except: settings[k] = v

            return settings
    except Exception as e:
        print(f"Error in get_settings: {e}")
        return defaults
    finally:
        if conn: conn.close()

@app.post("/api/admin/settings/update")
async def update_settings(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "فشل الاتصال بقاعدة البيانات"}
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE settings SET value = %s WHERE key = %s", (str(data['value']), data['key']))
            conn.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error in update_settings: {e}")
        return {"success": False, "msg": str(e)}
    finally:
        if conn: conn.close()

@app.post("/api/auth/register")
async def register(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "قاعدة البيانات غير متصلة"}
    try:
        with conn.cursor() as cur:
            uid = random.randint(1000000, 9999999)
            cur.execute("INSERT INTO users (user_id, username_key, password_key, player_name, is_registered) VALUES (%s, %s, %s, %s, %s)",
                        (uid, data['username'], data['password'], data['name'], True))
            conn.commit()
        return {
            "success": True, 
            "user": {
                "user_id": uid,
                "username_key": data['username'],
                "player_name": data['name'],
                "password_key": data['password'],
                "saved_players": []
            }
        }
    except: return {"success": False, "msg": "اليوزر نيم مستخدم مسبقاً"}
    finally: conn.close()

@app.post("/api/auth/login")
async def login(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "قاعدة البيانات غير متصلة"}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT user_id, username_key, player_name, password_key, saved_players FROM users WHERE username_key = %s AND password_key = %s",
                        (data['username'], data['password']))
            user = cur.fetchone()
            if user and not user.get('saved_players'): user['saved_players'] = []
            return {"success": True, "user": user} if user else {"success": False, "msg": "بيانات الدخول خاطئة"}
    except Exception as e:
        print(f"Error in login: {e}")
        return {"success": False, "msg": "حدث خطأ أثناء تسجيل الدخول"}
    finally:
        if conn: conn.close()

@app.post("/api/auth/update")
async def update_profile(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "قاعدة البيانات غير متصلة"}
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET username_key = %s, password_key = %s, player_name = %s WHERE username_key = %s",
                        (data['username'], data['password'], data['name'], data['old_username']))
            conn.commit()
        return {"success": True}
    except: return {"success": False, "msg": "اليوزر نيم الجديد مستخدم مسبقاً"}
    finally: conn.close()

@app.post("/api/game/start")
async def start_game(data: dict):
    players = data.get('players', [])
    category = data.get('category', 'أكلات')

    conn = get_db_conn()
    words = []
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT word FROM words WHERE category = %s", (category,))
                words = [r[0].strip() for r in cur.fetchall()]
        finally: conn.close()

    if not words:
        words = [w.strip() for w in CATEGORIES.get(category, CATEGORIES["أكلات"])]

    try:
        correct = random.choice(words)
        roles = ["in"] * len(players)
        spy_idx = random.randint(0, len(players)-1)
        roles[spy_idx] = "spy"

        other = [w for w in words if w != correct]
        guesses = random.sample(other, min(len(other), 6)) + [correct]
        random.shuffle(guesses)

        q_seq = []
        n = len(players)
        for i in range(0, n, 2):
            if i+1 < n: q_seq.append({"f": players[i], "t": players[i+1]})
            else: q_seq.append({"f": players[i], "t": players[0]})
        for i in range(0, n, 2):
            if i+1 < n: q_seq.append({"f": players[i+1], "t": players[(i+2)%n]})

        return {"word": correct, "roles": roles, "guesses": guesses, "q_seq": q_seq, "spy_idx": spy_idx}
    except Exception as e:
        print(f"Error in start_game: {e}")
        return {"error": str(e)}

# --- Online Mode API ---

def cleanup_stale_rooms():
    conn = get_db_conn()
    if not conn: return
    try:
        with conn.cursor() as cur:
            # Delete stale players and rooms inactive for more than 30 minutes
            cur.execute("DELETE FROM room_players WHERE room_code IN (SELECT room_code FROM rooms WHERE updated_at < NOW() - INTERVAL '30 minutes')")
            cur.execute("DELETE FROM rooms WHERE updated_at < NOW() - INTERVAL '30 minutes'")
            conn.commit()
    except Exception as e:
        print(f"Cleanup stale rooms error: {e}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()

@app.post("/api/online/create")
async def create_room(data: dict):
    conn = get_db_conn()
    if not conn:
        return {"success": False, "msg": "فشل الاتصال بقاعدة البيانات"}

    uid_raw = data.get('user_id')
    if uid_raw is None:
        return {"success": False, "msg": "معرف المستخدم مفقود. يرجى إعادة تسجيل الدخول."}

    try:
        user_id = int(uid_raw)
    except Exception:
        return {"success": False, "msg": "معرف المستخدم غير صالح. يرجى إعادة تسجيل الدخول."}

    player_name = str(data.get('player_name', 'لاعب'))[:100]
    room_code = None

    try:
        cleanup_stale_rooms()
        with conn.cursor() as cur:

            cur.execute("""
                INSERT INTO users (user_id, player_name, is_registered)
                VALUES (%s, %s, TRUE)
                ON CONFLICT (user_id) DO UPDATE SET player_name = EXCLUDED.player_name
            """, (user_id, player_name))

            for _ in range(5):
                candidate = ''.join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=5))
                cur.execute("SELECT 1 FROM rooms WHERE room_code = %s", (candidate,))
                if not cur.fetchone():
                    room_code = candidate
                    break

            if not room_code:
                raise Exception("تعذر إنشاء رمز غرفة فريد. حاول مرة أخرى.")

            cur.execute("""
                INSERT INTO rooms (room_code, room_id, host_id, creator_id, status, category, win_limit)
                VALUES (%s, %s, %s, %s, 'waiting', 'أكلات', 10)
            """, (room_code, room_code, user_id, user_id))

            cur.execute("""
                INSERT INTO room_players (room_code, room_id, user_id, player_name, is_ready, join_order, score)
                VALUES (%s, %s, %s, %s, TRUE, 1, 0)
                ON CONFLICT (room_code, user_id) DO UPDATE
                SET is_ready = TRUE, join_order = 1, player_name = EXCLUDED.player_name
            """, (room_code, room_code, user_id, player_name))

            conn.commit()
        return {"success": True, "room_code": room_code}
    except Exception as e:
        if conn: conn.rollback()
        import sys
        print(f"!!! DATABASE ERROR IN create_room: {e}", file=sys.stderr)
        return {"success": False, "msg": f"خطأ تقني في إنشاء الغرفة: {str(e)}"}
    finally:
        if conn: conn.close()

@app.post("/api/online/join")
async def join_room(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "DB Error"}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])
        player_name = data['player_name']
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT status FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room: return {"success": False, "msg": "الغرفة غير موجودة"}

            # التحقق من وجود اللاعب مسبقاً للحفاظ على ترتيبه والسماح بإعادة الانضمام
            cur.execute("SELECT join_order FROM room_players WHERE room_code = %s AND user_id = %s", (room_code, user_id))
            row = cur.fetchone()

            if not row and room['status'] != 'waiting':
                return {"success": False, "msg": "اللعبة بدأت بالفعل ولا يمكنك الانضمام كلاعب جديد"}

            if row:
                cur.execute("UPDATE room_players SET player_name = %s WHERE room_code = %s AND user_id = %s",
                            (player_name, room_code, user_id))
            else:
                cur.execute("SELECT COALESCE(MAX(join_order), 0) + 1 as next_order FROM room_players WHERE room_code = %s", (room_code,))
                next_order = cur.fetchone()['next_order']
                cur.execute("""
                    INSERT INTO room_players (room_code, room_id, user_id, player_name, join_order)
                    VALUES (%s, %s, %s, %s, %s)
                """, (room_code, room_code, user_id, player_name, next_order))
            conn.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error in join_room: {e}")
        return {"success": False, "msg": f"خطأ: {str(e)}"}
    finally:
        if conn: conn.close()

@app.post("/api/online/leave")
async def leave_online_room(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection failed"}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT 1 FROM room_players WHERE room_code = %s AND user_id = %s", (room_code, user_id))
            if not cur.fetchone():
                return {"success": True}
            
            cur.execute("DELETE FROM room_players WHERE room_code = %s AND user_id = %s", (room_code, user_id))
            
            cur.execute("SELECT user_id FROM room_players WHERE room_code = %s ORDER BY join_order ASC", (room_code,))
            remaining = cur.fetchall()
            if not remaining:
                cur.execute("DELETE FROM rooms WHERE room_code = %s", (room_code,))
            else:
                cur.execute("SELECT host_id FROM rooms WHERE room_code = %s", (room_code,))
                host_row = cur.fetchone()
                if host_row and host_row['host_id'] == user_id:
                    new_host_id = remaining[0]['user_id']
                    cur.execute("UPDATE rooms SET host_id = %s WHERE room_code = %s", (new_host_id, room_code))
            conn.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error in leave_room: {e}")
        return {"success": False, "msg": str(e)}
    finally:
        if conn: conn.close()

@app.post("/api/online/vote")
async def online_vote(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        room_code = data['room_code'].upper()
        user_id = data['user_id']
        vote_type = data['type'] # 'limit' or 'category'
        val = data['value']

        with conn.cursor() as cur:
            if vote_type == 'limit':
                cur.execute("UPDATE room_players SET vote_limit = %s WHERE room_code = %s AND user_id = %s", (int(val), room_code, user_id))
            else:
                cur.execute("UPDATE room_players SET vote_cat = %s WHERE room_code = %s AND user_id = %s", (val, room_code, user_id))
            conn.commit()
        return {"success": True}
    finally: conn.close()

@app.post("/api/online/start")
async def start_online_game(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "لا يوجد اتصال بقاعدة البيانات"}
    try:
        room_code = data['room_code'].upper()
        with conn.cursor() as cur:
            cur.execute("SELECT host_id FROM rooms WHERE room_code = %s", (room_code,))
            r = cur.fetchone()
            if not r: return {"success": False, "msg": "الغرفة غير موجودة"}
            if r[0] != data['user_id']: return {"success": False, "msg": "فقط المضيف يمكنه البدء"}

            # التأكد من عدد اللاعبين
            cur.execute("SELECT COUNT(*) FROM room_players WHERE room_code = %s", (room_code,))
            if cur.fetchone()[0] < 3: return {"success": False, "msg": "يجب وجود 3 لاعبين على الأقل"}

            # الانتقال لمرحلة التصويت على النقاط
            game_data = {"phase_start": time.time()}
            cur.execute("UPDATE rooms SET status = 'voting_limit', game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
            conn.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error in start_online_game: {e}")
        return {"success": False, "msg": f"خطأ: {str(e)}"}
    finally:
        if conn: conn.close()

@app.post("/api/online/submit_vote")
async def submit_vote(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection failed"}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])
        vote_type = data['type'] # 'limit' or 'cat'
        val = data['value']

        should_prepare = False
        with conn.cursor() as cur:
            if vote_type == 'limit':
                cur.execute("UPDATE room_players SET vote_limit = %s WHERE room_code = %s AND user_id = %s", (int(val), room_code, user_id))
            else:
                cur.execute("UPDATE room_players SET vote_cat = %s WHERE room_code = %s AND user_id = %s", (val, room_code, user_id))

            # التحقق هل الجميع صوتوا؟
            cur.execute(f"SELECT COUNT(*) FROM room_players WHERE room_code = %s AND vote_{vote_type} IS NULL", (room_code,))
            if cur.fetchone()[0] == 0:
                # حساب النتيجة
                cur.execute(f"SELECT vote_{vote_type}, COUNT(*) as c FROM room_players WHERE room_code = %s GROUP BY vote_{vote_type} ORDER BY c DESC LIMIT 1", (room_code,))
                winner = cur.fetchone()[0]

                if vote_type == 'limit':
                    cur.execute("SELECT game_data FROM rooms WHERE room_code = %s", (room_code,))
                    g_row = cur.fetchone()
                    g_data = g_row[0] if g_row and g_row[0] else {}
                    g_data['phase_start'] = time.time()
                    cur.execute("UPDATE rooms SET win_limit = %s, status = 'voting_cat', game_data = %s WHERE room_code = %s", (winner, json.dumps(g_data), room_code))
                else:
                    cur.execute("UPDATE rooms SET category = %s, status = 'roles_prep' WHERE room_code = %s", (winner, room_code))
                    should_prepare = True

            conn.commit()

        # Commit and close first before calling prepare_round to prevent deadlocks and connection leaks!
        conn.close()
        conn = None

        if should_prepare:
            await prepare_round(room_code)

        return {"success": True}
    except Exception as e:
        print(f"Error in submit_vote: {e}")
        return {"success": False, "msg": str(e)}
    finally:
        if conn: conn.close()

async def prepare_round(room_code):
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT category FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            cat = room['category']

            cur.execute("SELECT word FROM words WHERE category = %s", (cat,))
            words = [r['word'].strip() for r in cur.fetchall()]
            if not words: words = ["بيتزا", "شاورما", "منسف"] # افتراضي

            correct = random.choice(words)
            cur.execute("SELECT user_id, player_name, red_card FROM room_players WHERE room_code = %s ORDER BY join_order ASC, user_id ASC", (room_code,))
            players = cur.fetchall()

            spy_idx = random.randint(0, len(players)-1)
            spy_id = players[spy_idx]['user_id']

            # Reset players' readiness for role reveal
            cur.execute("UPDATE room_players SET is_ready = FALSE WHERE room_code = %s", (room_code,))

            # Filter active players for the question sequence
            active_players = [p for p in players if not p['red_card']]
            if len(active_players) < 3:
                 active_players = players

            q_seq = []
            n = len(active_players)
            for i in range(n):
                asker = active_players[i]
                answerer = active_players[(i+1)%n]
                q_seq.append({"asker_id": asker['user_id'], "asker_name": asker['player_name'],
                              "ans_id": answerer['user_id'], "ans_name": answerer['player_name'],
                              "status": "pending"})

            other = [w for w in words if w != correct]
            guesses = random.sample(other, min(len(other), 6)) + [correct]
            random.shuffle(guesses)

            game_data = {
                "word": correct,
                "spy_id": spy_id,
                "q_seq": q_seq,
                "q_idx": 0,
                "guesses": guesses,
                "messages": [],
                "phase_start": time.time(),
                "phase_timeout": 0
            }

            cur.execute("UPDATE rooms SET status = 'playing_roles', secret_word = %s, spy_id = %s, game_data = %s WHERE room_code = %s",
                        (correct, spy_id, json.dumps(game_data), room_code))
            conn.commit()
    finally: conn.close()

async def calculate_online_results(room_code):
    conn = get_db_conn()
    if not conn: return
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            game_data = room['game_data']
            spy_id = room['spy_id']
            votes = game_data.get('votes', {}) # user_id_str -> target_id (int)

            # Count votes
            vote_counts = {}
            for v_id_str, target_id in votes.items():
                target_id = int(target_id)
                vote_counts[target_id] = vote_counts.get(target_id, 0) + 1

            # Determine who got the most votes
            max_votes = -1
            voted_out_id = None
            for p_id, count in vote_counts.items():
                if count > max_votes:
                    max_votes = count
                    voted_out_id = p_id
                elif count == max_votes:
                    voted_out_id = None # Tie

            spy_caught = (voted_out_id == spy_id)
            game_data['spy_caught'] = spy_caught

            # Points distribution
            # 1. Players who voted for the spy (and are not red-carded) get 1 point
            for voter_id_str, target_id in votes.items():
                voter_id = int(voter_id_str)
                if int(target_id) == spy_id:
                    cur.execute("UPDATE room_players SET score = score + 1 WHERE room_code = %s AND user_id = %s AND red_card = FALSE", (room_code, voter_id))

            # 2. Spy gets point if NOT caught and not red-carded
            if not spy_caught:
                cur.execute("UPDATE room_players SET score = score + 1 WHERE room_code = %s AND user_id = %s AND red_card = FALSE", (room_code, spy_id))

            # 3. Handle Game Over and session points persistence
            cur.execute("SELECT user_id, score FROM room_players WHERE room_code = %s", (room_code,))
            players_scores = cur.fetchall()

            game_over = False
            winner_id = None
            for p in players_scores:
                if p['score'] >= room['win_limit']:
                    game_over = True
                    winner_id = p['user_id']
                    break

            if game_over:
                game_data['game_over'] = True
                game_data['winner_id'] = winner_id
                # Persist to global user profile (online_points)
                cur.execute("UPDATE users SET online_points = online_points + 1 WHERE user_id = %s", (winner_id,))
                cur.execute("UPDATE rooms SET status = 'result' WHERE room_code = %s", (room_code,))
            elif not spy_caught:
                cur.execute("UPDATE rooms SET status = 'result' WHERE room_code = %s", (room_code,))
            else:
                # Spy caught, move to guess phase
                cur.execute("UPDATE rooms SET status = 'spy_reveal' WHERE room_code = %s", (room_code,))

            cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
            conn.commit()
    except Exception as e:
        print(f"Error in calculate_online_results: {e}")
    finally:
        if conn: conn.close()

@app.get("/api/online/room/{room_code}")
async def get_room(room_code: str):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "No DB connection"}
    try:
        room_code = room_code.upper()
        should_prepare = False
        should_calculate_results = False
        changed = False

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Update updated_at keepalive timestamp
            cur.execute("UPDATE rooms SET updated_at = CURRENT_TIMESTAMP WHERE room_code = %s", (room_code,))
            conn.commit()
            
            # 2. Fetch the room
            cur.execute("SELECT * FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room: return {"success": False, "msg": "Room not found"}

            status = room['status']
            game_data = room['game_data'] or {}

            # --- Timeout and Auto-Transitions Checks ---
            if status == 'voting_limit':
                phase_start = game_data.get('phase_start')
                if phase_start and (time.time() - phase_start > 10):
                    cur.execute("SELECT user_id FROM room_players WHERE room_code = %s AND vote_limit IS NULL", (room_code,))
                    missing_voters = cur.fetchall()
                    for p in missing_voters:
                        random_limit = random.choice([5, 10, 15, 20])
                        cur.execute("UPDATE room_players SET vote_limit = %s WHERE room_code = %s AND user_id = %s", (random_limit, room_code, p['user_id']))
                    
                    cur.execute("SELECT vote_limit, COUNT(*) as c FROM room_players WHERE room_code = %s GROUP BY vote_limit ORDER BY c DESC LIMIT 1", (room_code,))
                    winner_row = cur.fetchone()
                    winner = winner_row['vote_limit'] if winner_row else 10
                    
                    game_data['phase_start'] = time.time()
                    cur.execute("UPDATE rooms SET win_limit = %s, status = 'voting_cat', game_data = %s WHERE room_code = %s", (winner, json.dumps(game_data), room_code))
                    changed = True

            elif status == 'voting_cat':
                phase_start = game_data.get('phase_start')
                if phase_start and (time.time() - phase_start > 10):
                    cur.execute("SELECT user_id FROM room_players WHERE room_code = %s AND vote_cat IS NULL", (room_code,))
                    missing_voters = cur.fetchall()
                    available_cats = ["أكلات", "حيوانات", "ملابس", "كورة", "سيارات", "شركات", "كواكب", "أجهزة", "تطبيقات", "فواكه وخضار", "شخصيات", "كارتون", "مشروبات", "حلويات", "مسلسلات", "انمي", "كيبوب", "قيمرز", "مهن"]
                    for p in missing_voters:
                        random_cat = random.choice(available_cats)
                        cur.execute("UPDATE room_players SET vote_cat = %s WHERE room_code = %s AND user_id = %s", (random_cat, room_code, p['user_id']))
                    
                    cur.execute("SELECT vote_cat, COUNT(*) as c FROM room_players WHERE room_code = %s GROUP BY vote_cat ORDER BY c DESC LIMIT 1", (room_code,))
                    winner_row = cur.fetchone()
                    winner = winner_row['vote_cat'] if winner_row else "أكلات"
                    
                    cur.execute("UPDATE rooms SET category = %s, status = 'roles_prep' WHERE room_code = %s", (winner, room_code))
                    changed = True
                    should_prepare = True

            elif status == 'voting_spy':
                phase_start = game_data.get('phase_start')
                if phase_start and (time.time() - phase_start > 10):
                    cur.execute("SELECT user_id FROM room_players WHERE room_code = %s AND is_ready = FALSE AND red_card = FALSE", (room_code,))
                    missing_voters = cur.fetchall()
                    
                    cur.execute("SELECT user_id FROM room_players WHERE room_code = %s", (room_code,))
                    all_players = [p['user_id'] for p in cur.fetchall()]
                    
                    if 'votes' not in game_data: game_data['votes'] = {}
                    for p in missing_voters:
                        voter_id = p['user_id']
                        possible_targets = [pid for pid in all_players if pid != voter_id]
                        if possible_targets:
                            random_target = random.choice(possible_targets)
                            game_data['votes'][str(voter_id)] = random_target
                            cur.execute("UPDATE room_players SET is_ready = TRUE WHERE room_code = %s AND user_id = %s", (room_code, voter_id))
                    
                    cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                    cur.execute("SELECT COUNT(*) FROM room_players WHERE room_code = %s AND is_ready = FALSE AND red_card = FALSE", (room_code,))
                    if cur.fetchone()['count'] == 0:
                        should_calculate_results = True
                    changed = True

            elif status == 'playing_questions':
                q_idx = game_data.get('q_idx', 0)
                q_seq = game_data.get('q_seq', [])
                if q_idx < len(q_seq):
                    curr_q = q_seq[q_idx]
                    elapsed = time.time() - game_data.get('phase_start', time.time())

                    # 15s to ask, 20s to answer
                    timeout = 15 if curr_q['status'] in ['pending', 'asking'] else 20

                    if elapsed > timeout:
                        target_user_id = curr_q['asker_id'] if curr_q['status'] in ['pending', 'asking'] else curr_q['ans_id']

                        cur.execute("UPDATE room_players SET yellow_cards = yellow_cards + 1 WHERE room_code = %s AND user_id = %s", (room_code, target_user_id))
                        cur.execute("SELECT yellow_cards FROM room_players WHERE room_code = %s AND user_id = %s", (room_code, target_user_id))
                        y_cards_row = cur.fetchone()
                        if y_cards_row and y_cards_row['yellow_cards'] >= 2:
                            cur.execute("UPDATE room_players SET red_card = TRUE WHERE room_code = %s AND user_id = %s", (room_code, target_user_id))

                        curr_q['status'] = 'timeout'
                        game_data['q_idx'] += 1
                        game_data['phase_start'] = time.time()

                        if game_data['q_idx'] >= len(q_seq):
                            room['status'] = 'voting_spy'
                            game_data['phase_start'] = time.time()
                            cur.execute("UPDATE rooms SET status = 'voting_spy', game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                            cur.execute("UPDATE room_players SET is_ready = FALSE WHERE room_code = %s", (room_code,))

                        changed = True

            if changed:
                cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                conn.commit()
                # Re-fetch room if changed
                cur.execute("SELECT * FROM rooms WHERE room_code = %s", (room_code,))
                room = cur.fetchone()

            cur.execute("SELECT user_id, player_name, is_ready, score, yellow_cards, red_card FROM room_players WHERE room_code = %s ORDER BY join_order ASC, user_id ASC", (room_code,))
            players = cur.fetchall()

        # Commit and close connection first to prevent nested deadlocks!
        if conn:
            conn.commit()
            conn.close()
            conn = None

        if should_prepare:
            await prepare_round(room_code)
            conn_new = get_db_conn()
            try:
                with conn_new.cursor(cursor_factory=RealDictCursor) as cur_new:
                    cur_new.execute("SELECT * FROM rooms WHERE room_code = %s", (room_code,))
                    room = cur_new.fetchone()
                    cur_new.execute("SELECT user_id, player_name, is_ready, score, yellow_cards, red_card FROM room_players WHERE room_code = %s ORDER BY join_order ASC, user_id ASC", (room_code,))
                    players = cur_new.fetchall()
            finally:
                conn_new.close()

        if should_calculate_results:
            await calculate_online_results(room_code)
            conn_new = get_db_conn()
            try:
                with conn_new.cursor(cursor_factory=RealDictCursor) as cur_new:
                    cur_new.execute("SELECT * FROM rooms WHERE room_code = %s", (room_code,))
                    room = cur_new.fetchone()
                    cur_new.execute("SELECT user_id, player_name, is_ready, score, yellow_cards, red_card FROM room_players WHERE room_code = %s ORDER BY join_order ASC, user_id ASC", (room_code,))
                    players = cur_new.fetchall()
            finally:
                conn_new.close()

        # Compute time_left server-side to avoid timezone/clock desync
        time_left = 0
        if room:
            status = room.get('status')
            game_data = room.get('game_data') or {}
            if isinstance(game_data, str):
                try:
                    game_data = json.loads(game_data)
                except:
                    game_data = {}
            
            phase_start = game_data.get('phase_start')
            if phase_start:
                elapsed = time.time() - phase_start
                if status in ['voting_limit', 'voting_cat', 'voting_spy']:
                    time_left = max(0, int(10 - elapsed))
                elif status == 'playing_questions':
                    q_idx = game_data.get('q_idx', 0)
                    q_seq = game_data.get('q_seq', [])
                    if q_idx < len(q_seq):
                        curr_q = q_seq[q_idx]
                        limit = 20 if curr_q.get('status') == 'answering' else 15
                        time_left = max(0, int(limit - elapsed))
            
            room_dict = dict(room)
            room_dict['time_left'] = time_left
            room = room_dict

        return {"success": True, "room": room, "players": players}
    except Exception as e:
        print(f"Error in get_room: {e}")
        return {"success": False, "msg": str(e)}
    finally:
        if conn: conn.close()

@app.post("/api/online/action")
async def online_action(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "No DB connection"}
    try:
        room_code = data['room_code'].upper()
        user_id = data['user_id']
        action = data['action']

        should_calculate_results = False
        should_prepare_round = False

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room: return {"success": False, "msg": "Room not found"}

            game_data = room['game_data']

            if action == "ready_role":
                # تسجيل أن اللاعب قرأ دوره
                cur.execute("UPDATE room_players SET is_ready = TRUE WHERE room_code = %s AND user_id = %s", (room_code, user_id))
                # إذا الكل جاهز، ننتقل للمرحلة التالية
                cur.execute("SELECT COUNT(*) FROM room_players WHERE room_code = %s AND is_ready = FALSE", (room_code,))
                if cur.fetchone()['count'] == 0:
                    game_data['phase_start'] = time.time()
                    cur.execute("UPDATE rooms SET status = 'playing_questions', game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                    # ريست لـ is_ready لاستخدامها لاحقاً
                    cur.execute("UPDATE room_players SET is_ready = FALSE WHERE room_code = %s", (room_code,))
                conn.commit()

            elif action == "submit_question":
                # Check if red carded
                cur.execute("SELECT red_card FROM room_players WHERE room_code = %s AND user_id = %s", (room_code, user_id))
                res = cur.fetchone()
                if res and res['red_card']: return {"success": False, "msg": "أنت مستبعد (كرت أحمر)"}

                q_idx = game_data.get('q_idx', 0)
                if q_idx < len(game_data['q_seq']):
                    curr_q = game_data['q_seq'][q_idx]
                    if curr_q['asker_id'] == user_id and curr_q['status'] in ['pending', 'asking']:
                        curr_q['question'] = data['text']
                        curr_q['status'] = 'answering'
                        game_data['phase_start'] = time.time()
                        cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                conn.commit()

            elif action == "submit_answer":
                # Check if red carded
                cur.execute("SELECT red_card FROM room_players WHERE room_code = %s AND user_id = %s", (room_code, user_id))
                res = cur.fetchone()
                if res and res['red_card']: return {"success": False, "msg": "أنت مستبعد (كرت أحمر)"}

                q_idx = game_data.get('q_idx', 0)
                if q_idx < len(game_data['q_seq']):
                    curr_q = game_data['q_seq'][q_idx]
                    if curr_q['ans_id'] == user_id and curr_q['status'] == 'answering':
                        curr_q['answer'] = data['text']
                        curr_q['status'] = 'done'
                        game_data['q_idx'] += 1
                        game_data['phase_start'] = time.time()

                        if game_data['q_idx'] >= len(game_data['q_seq']):
                            game_data['phase_start'] = time.time()
                            cur.execute("UPDATE rooms SET status = 'voting_spy' WHERE room_code = %s", (room_code,))
                            cur.execute("UPDATE room_players SET is_ready = FALSE WHERE room_code = %s", (room_code,))

                        cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                conn.commit()

            elif action == "vote":
                # Check if red carded
                cur.execute("SELECT red_card FROM room_players WHERE room_code = %s AND user_id = %s", (room_code, user_id))
                res = cur.fetchone()
                if res and res['red_card']: return {"success": False, "msg": "أنت مستبعد (كرت أحمر)"}

                target_id = int(data['target_id'])
                if 'votes' not in game_data: game_data['votes'] = {}
                game_data['votes'][str(user_id)] = target_id

                cur.execute("UPDATE room_players SET is_ready = TRUE WHERE room_code = %s AND user_id = %s", (room_code, user_id))

                # إذا الكل صوت (باستثناء المستبعدين بالكرت الأحمر)
                cur.execute("SELECT COUNT(*) FROM room_players WHERE room_code = %s AND is_ready = FALSE AND red_card = FALSE", (room_code,))
                if cur.fetchone()['count'] == 0:
                    # Calculate results
                    cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                    conn.commit() # Save votes first
                    should_calculate_results = True
                else:
                    cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                    conn.commit()

            elif action == "spy_guess":
                guess = data['guess']
                game_data['spy_guess'] = guess
                room_code = data['room_code'].upper()

                # توزيع النقاط إذا خمن صح
                if guess == room['secret_word']:
                    cur.execute("UPDATE room_players SET score = score + 1 WHERE room_code = %s AND user_id = %s", (room_code, user_id))

                # Check for Game Over after spy guess
                cur.execute("SELECT user_id, score FROM room_players WHERE room_code = %s", (room_code,))
                players_scores = cur.fetchall()

                game_over = False
                winner_id = None
                for p in players_scores:
                    if p['score'] >= room['win_limit']:
                        game_over = True
                        winner_id = p['user_id']
                        break

                if game_over:
                    game_data['game_over'] = True
                    game_data['winner_id'] = winner_id
                    cur.execute("UPDATE users SET online_points = online_points + 1 WHERE user_id = %s", (winner_id,))

                cur.execute("UPDATE rooms SET status = 'result', game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                conn.commit()

            elif action == "new_round":
                if room['host_id'] == user_id:
                    should_prepare_round = True

        # Commit and close connection first to prevent nested deadlocks!
        if should_calculate_results or should_prepare_round:
            conn.close()
            conn = None
            if should_calculate_results:
                await calculate_online_results(room_code)
            elif should_prepare_round:
                await prepare_round(room_code)

        return {"success": True}
    except Exception as e:
        print(f"Error in online_action: {e}")
        return {"success": False, "msg": str(e)}
    finally:
        if conn: conn.close()

@app.post("/api/admin/add_word")
async def add_word(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection failed"}
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO words (category, word) VALUES (%s, %s)", (data['category'], data['word']))
            conn.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error in add_word: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@app.get("/api/admin/words")
async def get_words():
    conn = get_db_conn()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM words ORDER BY category, word")
            return cur.fetchall()
    except Exception as e:
        print(f"Error in get_words: {e}")
        return []
    finally: conn.close()

# --- Admin Dashboard APIs ---

@app.get("/api/online/rankings")
async def get_online_rankings():
    conn = get_db_conn()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT player_name, online_points FROM users WHERE online_points > 0 ORDER BY online_points DESC LIMIT 50")
            return cur.fetchall()
    except Exception as e:
        print(f"Error in get_online_rankings: {e}")
        return []
    finally: conn.close()

@app.get("/api/admin/players")
async def admin_get_players():
    conn = get_db_conn()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT user_id, username_key, player_name, total_wins FROM users ORDER BY total_wins DESC")
            return cur.fetchall()
    except Exception as e:
        print(f"Error in admin_get_players: {e}")
        return []
    finally: conn.close()

@app.get("/api/categories")
async def get_categories():
    conn = get_db_conn()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM categories ORDER BY display_order ASC, name ASC")
            cats = cur.fetchall()
            # إذا الجدول فارغ، نعبئه بالبيانات الافتراضية
            if not cats:
                default_cats = ["أكلات", "حيوانات", "ملابس", "كورة", "سيارات", "شركات", "كواكب", "أجهزة", "تطبيقات", "فواكه وخضار", "شخصيات", "كارتون", "مشروبات", "حلويات", "مسلسلات", "انمي", "كيبوب", "قيمرز", "مهن"]
                for i, c in enumerate(default_cats):
                    cur.execute("INSERT INTO categories (name, display_order) VALUES (%s, %s) ON CONFLICT DO NOTHING", (c, i))
                conn.commit()
                cur.execute("SELECT * FROM categories ORDER BY display_order ASC, name ASC")
                cats = cur.fetchall()
            # الترحيل: إذا كانت قاعدة البيانات فارغة من الكلمات، انقل الكلمات الافتراضية إليها
            cur.execute("SELECT COUNT(*) FROM words")
            if cur.fetchone()['count'] == 0:
                for cat, word_list in CATEGORIES.items():
                    for word in word_list:
                        cur.execute("INSERT INTO words (category, word) VALUES (%s, %s) ON CONFLICT DO NOTHING", (cat, word))
                conn.commit()

            return cats
    finally: conn.close()

@app.post("/api/admin/category/add")
async def add_category(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection failed"}
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO categories (name, image_url, display_order) VALUES (%s, %s, %s)",
                        (data['name'], data.get('image_url'), data.get('display_order', 0)))
            conn.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error in add_category: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@app.post("/api/admin/category/update")
async def update_category(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection failed"}
    try:
        with conn.cursor() as cur:
            # تحديث اسم الفئة في جدول الكلمات أولاً إذا تغير الاسم
            if 'old_name' in data and data['old_name'] != data['name']:
                cur.execute("UPDATE words SET category = %s WHERE category = %s", (data['name'], data['old_name']))

            cur.execute("UPDATE categories SET name = %s, image_url = %s, display_order = %s WHERE id = %s",
                        (data['name'], data.get('image_url'), data.get('display_order', 0), data['id']))
            conn.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error in update_category: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@app.post("/api/admin/category/delete")
async def delete_category(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection failed"}
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM categories WHERE id = %s", (data['id'],))
            conn.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error in delete_category: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@app.post("/api/admin/word/update")
async def update_word(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection failed"}
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE words SET word = %s WHERE id = %s", (data['word'], data['id']))
            conn.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error in update_word: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@app.post("/api/admin/word/delete")
async def delete_word(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection failed"}
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM words WHERE id = %s", (data['id'],))
            conn.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error in delete_word: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@app.post("/api/user/save_players")
async def save_players(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection failed"}
    try:
        user_id = int(data['user_id'])
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET saved_players = %s WHERE user_id = %s",
                        (json.dumps(data['players']), user_id))
            conn.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error in save_players: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@app.post("/api/game/report_winner")
async def report_winner(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection failed"}
    try:
        with conn.cursor() as cur:
            # تحديث اللاعب في جدول المستخدمين الرئيسي (إذا كان مسجلاً)
            cur.execute("UPDATE users SET total_wins = total_wins + 1 WHERE player_name = %s", (data['player_name'],))

            # تحديث قائمة اللاعبين المحليين للمستخدم الحالي (Host)
            if 'user_id' in data:
                user_id = int(data['user_id'])
                cur.execute("SELECT saved_players FROM users WHERE user_id = %s", (user_id,))
                row = cur.fetchone()
                if row:
                    players = row[0] if row[0] is not None else []
                    updated = False
                    for i, p in enumerate(players):
                        p_name = p if isinstance(p, str) else p.get('name')
                        if p_name == data['player_name']:
                            if isinstance(p, str):
                                players[i] = {"name": p, "wins": 1}
                            else:
                                p['wins'] = p.get('wins', 0) + 1
                            updated = True
                            break
                    if updated:
                        cur.execute("UPDATE users SET saved_players = %s WHERE user_id = %s", (json.dumps(players), user_id))
            conn.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error in report_winner: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>برا السالفة | المجلس</title>
    <link rel="icon" href="data:,">
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#6c5ce7">
    <link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/8030/8030198.png">
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #6c5ce7; --bg: #0f0c29; --card: #1b1464; --accent: #f9ca24; --error: #eb4d4b; --success: #2ecc71; }
        body { font-family: 'Cairo', sans-serif; background: var(--bg); color: white; margin: 0; min-height: 100vh; }
        .flex-center { display: flex; justify-content: center; align-items: center; min-height: 100vh; flex-direction: column; }
        .container { width: 98%; text-align: center; padding: 5px; box-sizing: border-box; }
        .card { background: var(--card); padding: 24px 16px; border-radius: 24px; box-shadow: 0 15px 35px rgba(0,0,0,0.6); border: 2px solid #3c339e; animation: fadeIn 0.3s ease; width: 100%; box-sizing: border-box; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideIn { from { transform: translateX(100px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .reveal-text { animation: pop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
        @keyframes pop { 0% { transform: scale(0.5); } 100% { transform: scale(1); } }
        h1 { font-weight: 900; color: #a29bfe; margin-bottom: 25px; font-size: 32px; }
        input, select { width: 100%; padding: 15px; margin: 10px 0; border-radius: 15px; border: 2px solid #2f278c; background: #0f0c29; color: white; font-size: 16px; box-sizing: border-box; outline: none; }
        button { width: 100%; padding: 16px; margin: 12px 0; border-radius: 18px; border: none; background: linear-gradient(45deg, #6c5ce7, #a29bfe); color: white; font-weight: bold; cursor: pointer; font-size: 18px; transition: 0.3s; }
        button:hover { transform: translateY(-3px); }
        button:disabled { opacity: 0.6; cursor: not-allowed; transform: none !important; }
        .btn-yellow { background: linear-gradient(45deg, #f9ca24, #f1c40f) !important; color: #1b1464 !important; box-shadow: 0 5px 15px rgba(249, 202, 36, 0.4); }
        .btn-yellow:hover { background: linear-gradient(45deg, #f1c40f, #f9ca24) !important; }
        .sidebar { position: fixed; right: -280px; top: 0; width: 280px; height: 100vh; background: #130f40; transition: 0.4s; z-index: 1000; padding: 30px 20px; box-sizing: border-box; border-left: 2px solid var(--primary); overflow-y: auto; display: flex; flex-direction: column; gap: 5px; }
        .sidebar::-webkit-scrollbar { width: 5px; }
        .sidebar::-webkit-scrollbar-thumb { background: var(--primary); border-radius: 10px; }
        .sidebar.open { right: 0; }
        .menu-btn { position: fixed; right: 20px; top: 20px; font-size: 28px; cursor: pointer; z-index: 1001; background: var(--card); width: 50px; height: 50px; border-radius: 15px; text-align: center; line-height: 50px; }
        .vote-item { background: #2f278c; padding: 18px; margin: 10px 0; border-radius: 20px; cursor: pointer; transition: 0.2s; font-weight: bold; }
        .vote-item:hover { background: var(--primary); transform: scale(1.02); }
        .hidden { display: none !important; }
        .toast {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(46, 204, 113, 0.95);
            color: white;
            padding: 12px 25px;
            border-radius: 50px;
            font-size: 16px;
            font-weight: bold;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            z-index: 10000;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease, transform 0.3s ease;
            direction: rtl;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .toast.show {
            opacity: 1;
            transform: translate(-50%, -10px);
        }
        .q-badge { background: var(--error); padding: 4px 12px; border-radius: 8px; font-size: 13px; margin-bottom: 15px; display: inline-block; }
        .shuffling { animation: rotate 1s infinite linear; font-size: 50px; margin: 20px; display:inline-block; }
        .score-item { display: flex; justify-content: space-between; background: #0f0c29; padding: 10px 20px; border-radius: 10px; margin: 5px 0; border: 1px solid #3c339e; }
        .cat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 20px 0; max-height: 340px; overflow-y: auto; padding: 10px; }
        .cat-card { background: #130f40; border-radius: 15px; padding: 10px; cursor: pointer; border: 2px solid transparent; transition: 0.3s; display: flex; flex-direction: column; align-items: center; min-height: 170px; }
        .cat-card.placeholder { opacity: 0.7; filter: blur(0.5px); }
        .cat-card img { width: 100%; height: 120px; object-fit: cover; border-radius: 12px; margin-bottom: 8px; opacity: 0; transition: opacity 0.25s ease-in-out; }
        .cat-card.selected { border-color: var(--accent); background: #1b1464; box-shadow: 0 0 15px var(--accent); }
        .cat-image-wrapper { position: relative; width: 100%; }
        .image-placeholder { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: #1a1538; border-radius: 12px; color: #9aa0b4; font-size: 18px; pointer-events: none; }
        .win-opt {
            padding: 10px 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            cursor: pointer;
            transition: 0.3s;
            border: 2px solid transparent;
            font-weight: bold;
        }
        .win-opt.selected {
            background: var(--accent);
            color: white;
            border-color: white;
        }
        .cat-card span { font-size: 12px; font-weight: bold; }
        .loading-spinner {
            width: 48px;
            height: 48px;
            border: 5px solid rgba(255,255,255,0.15);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        .exit-btn { position: fixed; left: 20px; top: 20px; font-size: 20px; cursor: pointer; z-index: 1001; background: var(--error); width: 50px; height: 50px; border-radius: 15px; text-align: center; line-height: 50px; color: white; display: none; box-shadow: 0 4px 10px rgba(0,0,0,0.3); transition: 0.3s; }
        .exit-btn:hover { transform: scale(1.1); }
        .no-img { width: 100%; height: 60px; background: #2f278c; display: flex; align-items: center; justify-content: center; border-radius: 10px; font-size: 24px; }
        @keyframes rotate { from { transform: rotate(0); } to { transform: rotate(360deg); } }
        @keyframes spin { to { transform: rotate(360deg); } }
        .modal { display: none; position: fixed; z-index: 3000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); backdrop-filter: blur(5px); }
        .modal-content { background: var(--card); margin: 15% auto; padding: 25px; border: 2px solid var(--primary); width: 85%; max-width: 400px; border-radius: 25px; animation: pop 0.3s ease; text-align: center; }
        
        /* Premium Scrollable Q&A Chat History styling */
        .qa-chat-container {
            margin-top: 25px;
            background: rgba(15, 12, 41, 0.6);
            border: 2px solid #2f278c;
            border-radius: 20px;
            text-align: right;
            direction: rtl;
            overflow: hidden;
            box-shadow: inset 0 2px 10px rgba(0,0,0,0.5);
        }
        .qa-chat-header {
            background: #1b1464;
            padding: 10px 15px;
            font-size: 14px;
            font-weight: bold;
            color: var(--accent);
            border-bottom: 1px solid #2f278c;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .qa-chat-body {
            max-height: 180px;
            overflow-y: auto;
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .qa-chat-body::-webkit-scrollbar {
            width: 6px;
        }
        .qa-chat-body::-webkit-scrollbar-thumb {
            background: #2f278c;
            border-radius: 10px;
        }
        .qa-chat-item {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 10px 12px;
            border: 1px solid rgba(255,255,255,0.05);
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .qa-chat-q, .qa-chat-a {
            display: flex;
            align-items: baseline;
            gap: 6px;
            font-size: 14px;
            line-height: 1.5;
        }
        .qa-chat-badge {
            font-weight: bold;
            white-space: nowrap;
        }
        .qa-chat-badge.asker {
            color: #a29bfe;
        }
        .qa-chat-badge.answerer {
            color: #2ecc71;
        }
        .qa-chat-text {
            color: #e2e2e2;
            word-break: break-word;
        }

        /* Q&A Chat Layout Styles */
        .qa-chat-layout {
            display: flex;
            flex-direction: column;
            height: 520px; /* fixed height for chat card */
            max-height: 75vh;
            text-align: right;
            direction: rtl;
        }
        .qa-chat-header-main {
            padding-bottom: 12px;
            border-bottom: 2px solid #2f278c;
            margin-bottom: 10px;
        }
        .qa-chat-header-main h2 {
            margin: 0 0 6px 0;
            font-size: 22px;
            color: #a29bfe;
        }
        .qa-current-turn {
            font-size: 15px;
            background: rgba(255,255,255,0.05);
            padding: 6px 12px;
            border-radius: 12px;
            display: inline-block;
            border: 1px solid rgba(255,255,255,0.08);
        }
        .qa-chat-scroll-area {
            flex-grow: 1;
            overflow-y: auto;
            padding: 10px 5px;
            display: flex;
            flex-direction: column;
            gap: 15px;
            margin-bottom: 15px;
            background: rgba(15, 12, 41, 0.4);
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.05);
            box-shadow: inset 0 4px 15px rgba(0,0,0,0.4);
            scroll-behavior: smooth;
        }
        .qa-chat-scroll-area::-webkit-scrollbar {
            width: 5px;
        }
        .qa-chat-scroll-area::-webkit-scrollbar-thumb {
            background: var(--primary);
            border-radius: 10px;
        }
        .chat-message-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .chat-bubble {
            max-width: 85%;
            padding: 10px 14px;
            border-radius: 18px;
            font-size: 15px;
            line-height: 1.5;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            animation: pop 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.15);
        }
        .bubble-asker {
            background: linear-gradient(135deg, #2c256b, #1b1464);
            align-self: flex-start;
            border-bottom-right-radius: 4px;
            border: 1px solid #3c339e;
        }
        .bubble-answerer {
            background: linear-gradient(135deg, #10ac84, #0f9b76);
            align-self: flex-end;
            border-bottom-left-radius: 4px;
            color: white;
        }
        .bubble-typing {
            background: rgba(255,255,255,0.06);
            align-self: center;
            border: 1px dashed rgba(255,255,255,0.15);
            color: #9aa0b4;
            font-style: italic;
            text-align: center;
        }
        .bubble-sender {
            font-size: 11px;
            font-weight: bold;
            opacity: 0.85;
            margin-bottom: 4px;
        }
        .bubble-content {
            word-break: break-word;
        }
        .qa-chat-footer-input {
            border-top: 2px solid #2f278c;
            padding-top: 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .qa-timer-badge {
            align-self: center;
            font-size: 14px;
            font-weight: bold;
            color: var(--error);
            background: rgba(235, 77, 75, 0.1);
            padding: 4px 12px;
            border-radius: 8px;
            border: 1px solid rgba(235, 77, 75, 0.2);
        }
        .qa-input-box-wrapper {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .qa-typing-status {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 12px;
            text-align: center;
            font-size: 14px;
            color: #9aa0b4;
            border: 1px solid rgba(255,255,255,0.05);
        }
        @keyframes typing-dots {
            0%, 20% { content: "."; }
            40% { content: ".."; }
            60% { content: "..."; }
            80%, 100% { content: ""; }
        }
        .typing-dots::after {
            content: "";
            animation: typing-dots 1.5s infinite;
        }

        /* Responsive styling for larger screen devices */
        @media (min-width: 600px) {
            .container { max-width: 850px; width: 95%; }
            .card { padding: 45px 35px; border-radius: 40px; }
            button { font-size: 22px; padding: 20px; border-radius: 22px; }
            input, select { font-size: 20px; padding: 20px; border-radius: 20px; }
            h1 { font-size: 42px; }
            h2 { font-size: 34px; }
            h3 { font-size: 28px; }
            .vote-item { font-size: 20px; padding: 22px; }
            .qa-chat-body { max-height: 350px; }
        }
    </style>
</head>
<body>
    <div class="menu-btn" onclick="toggleSidebar()">☰</div>
    <div class="exit-btn" id="global-exit-btn" onclick="confirmExitGame()">✖</div>

    <!-- Install Prompt Modal -->
    <div id="installModal" class="modal">
        <div class="modal-content">
            <h2 style="color:var(--accent)">تثبيت التطبيق 📱</h2>
            <p>للحصول على أفضل تجربة، أضف اللعبة إلى شاشتك الرئيسية.</p>
            <button id="modal-install-btn" onclick="installApp()">✨ تثبيت التطبيق (PWA)</button>
            <button class="btn-yellow" onclick="showShortcutGuide()">📝 دليل الإضافة اليدوية</button>
            <button style="background:#636e72" onclick="closeInstallModal()">إغلاق</button>
        </div>
    </div>

    <div id="sidebar" class="sidebar">
        <h2 style="color:var(--accent)">القائمة</h2>
        <div style="background:#1b1464; padding:15px; border-radius:15px; margin:20px 0;">
            <p id="user-display" style="margin:0; font-weight:bold;">زائر</p>
        </div>
        <button id="install-btn-sidebar" style="background:var(--accent); color:black; font-size:14px;" onclick="showInstallOptions()">📲 إضافة للشاشة الرئيسية</button>
        <button style="background:var(--success); font-size:14px;" onclick="showReports()">📊 التقارير والمتصدرين</button>
        <button style="background:var(--primary); font-size:14px;" onclick="showEditProfile()">تعديل بيانات الحساب</button>
        <button style="background:var(--error); font-size:14px;" onclick="logout()">تسجيل الخروج</button>
        <button style="background:#636e72; font-size:14px;" onclick="toggleSidebar()">إغلاق</button>
    </div>
    <div class="flex-center"><div class="container" id="main-ui"></div></div>
    <script>
        let currentUser = null;
        try {
            currentUser = JSON.parse(localStorage.getItem('user')) || null;
        } catch (e) {
            console.error("Failed to parse user from localStorage:", e);
            localStorage.removeItem('user');
        }
        let game = null;
        let p_votes = {};
        let totalScores = {}; // نقاط الجلسة
        let winLimit = 1000;
        let questionTimeout = 30;
        let voteTimeout = 10;
        let spyGuessTimeout = 15;
        let soundClickUrl = '';
        let soundRevealUrl = '';
        let soundWinUrl = '';
        let soundFailUrl = '';
        let timerInterval = null;
        const DEFAULT_CATEGORIES = [
            'أكلات', 'حيوانات', 'ملابس', 'كورة', 'سيارات', 'شركات', 'كواكب', 'أجهزة', 'تطبيقات', 'فواكه وخضار', 'شخصيات', 'كارتون', 'مشروبات', 'حلويات', 'مسلسلات', 'انمي', 'كيبوب', 'قيمرز', 'مهن'
        ];

        async function fetchSettings() {
            try {
                const res = await fetch('/api/settings');
                const d = await res.json();
                questionTimeout = parseInt(d.question_timeout) || 30;
                voteTimeout = parseInt(d.vote_timeout) || 10;
                spyGuessTimeout = parseInt(d.spy_guess_timeout) || 15;

                if(d.sound_click && d.sound_click.startsWith('http')) {
                    soundClickUrl = d.sound_click;
                    sounds.click = new Audio(soundClickUrl);
                }
                if(d.sound_reveal && d.sound_reveal.startsWith('http')) {
                    soundRevealUrl = d.sound_reveal;
                    sounds.reveal = new Audio(soundRevealUrl);
                }
                if(d.sound_win && d.sound_win.startsWith('http')) {
                    soundWinUrl = d.sound_win;
                    sounds.win = new Audio(soundWinUrl);
                }
                if(d.sound_fail && d.sound_fail.startsWith('http')) {
                    soundFailUrl = d.sound_fail;
                    sounds.fail = new Audio(soundFailUrl);
                }
            } catch(e) { console.error("Settings fetch failed", e); }
        }

        function navigateTo(screen, data = {}, push = true) {
            lastRenderedHTML = "";
            if (push) {
                history.pushState({ screen, ...data }, "");
            }
            switch(screen) {
                case 'auth': showAuth(); break;
                case 'menu': showMenu(false); break;
                case 'online_menu': showOnlineMenu(false); break;
                case 'setup': showSetup(data.step, false); break;
                case 'reports': showReports(false); break;
                case 'global_rankings': showGlobalRankings(false); break;
                case 'edit_profile': showEditProfile(false); break;
                case 'admin': showAdminDashboard(false); break;
            }
        }

        window.onpopstate = function(event) {
            if (event.state && event.state.screen) {
                navigateTo(event.state.screen, event.state, false);
            } else {
                currentUser ? showMenu(false) : showAuth();
            }
        };

        const AUDIO = {
            tick: new Audio('https://www.soundjay.com/buttons/sounds/button-11.mp3'),
            warning: new Audio('https://www.soundjay.com/buttons/sounds/button-10.mp3'),
            penalty: new Audio('https://www.soundjay.com/buttons/sounds/button-4.mp3'),
            success: new Audio('https://www.soundjay.com/misc/sounds/bell-ringing-05.mp3')
        };
        let lastKnownStatus = null;
        let lastKnownCards = {};

        function init() {
            fetchSettings();
            // Check for /join/CODE path
            const pathParts = window.location.pathname.split('/');
            let joinCode = null;
            if (pathParts[1] === 'join' && pathParts[2]) {
                joinCode = pathParts[2];
                window.history.replaceState({}, document.title, "/");
            }

            // Also check for ?join=CODE param
            const urlParams = new URLSearchParams(window.location.search);
            if (!joinCode) joinCode = urlParams.get('join');

            if (joinCode) {
                if (!urlParams.get('join')) window.history.replaceState({}, document.title, window.location.pathname);
                localStorage.setItem('pendingJoin', joinCode);
            }

            if (currentUser) {
                showMenu(false);
                history.replaceState({ screen: 'menu' }, "");
            } else {
                showAuth();
            }

            updateSidebar();
            prefetchCategories();
            if (currentUser && localStorage.getItem('pendingJoin')) {
                const code = localStorage.getItem('pendingJoin');
                localStorage.removeItem('pendingJoin');
                joinRoomByCode(code);
            }
        }

        function showAuth() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h1>🕵️ برا السالفة</h1>
                    <input id="u_name" placeholder="اليوزر نيم">
                    <input id="u_pass" type="password" placeholder="الباسوورد">
                    <button onclick="login()">دخول</button>
                    <hr style="border:0; border-top:1px solid #3c339e; margin:20px 0;">
                    <input id="r_nick" placeholder="الاسم المستعار (يظهر للجميع)">
                    <button style="background:#4834d4" onclick="register()">إنشاء حساب</button>
                </div>`;
        }

        async function login() {
            try {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: u_name.value, password: u_pass.value})
                });
                if (!res.ok) throw new Error("Server error " + res.status);
                const d = await res.json();
                if(d.success) {
                    localStorage.setItem('user', JSON.stringify(d.user));
                    currentUser = d.user;
                    init();
                } else {
                    alert(d.msg);
                }
            } catch(e) {
                console.error("Login failed", e);
                alert("فشل تسجيل الدخول. تأكد من اتصالك بالإنترنت.");
            }
        }

        async function register() {
            if(!u_name.value || !u_pass.value || !r_nick.value) {
                showError("الرجاء تعبئة جميع الحقول المطلوبة لإنشاء حساب.", "بيانات التسجيل ناقصة");
                return;
            }
            try {
                const res = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: u_name.value, password: u_pass.value, name: r_nick.value})
                });
                if (!res.ok) throw new Error("Server error " + res.status);
                const d = await res.json();
                if(d.success) {
                    localStorage.setItem('user', JSON.stringify(d.user));
                    currentUser = d.user;
                    init();
                } else {
                    showError(d.msg || "اسم المستخدم غير متاح. الرجاء اختيار اسم مستخدم آخر.", "فشل التسجيل");
                }
            } catch(e) {
                console.error("Register failed", e);
                showError("فشل التسجيل. يرجى التحقق من اتصالك بالإنترنت والمحاولة مرة أخرى لاحقاً.", "خطأ في الاتصال");
            }
        }

        function showMenu(push = true) {
            if(timerInterval) clearInterval(timerInterval);
            if(push) history.pushState({screen: 'menu'}, "");
            if(document.getElementById('global-exit-btn')) document.getElementById('global-exit-btn').style.display = 'none';
            game = null;
            totalScores = {}; // ريست للنقاط عند العودة للقائمة
            document.getElementById('main-ui').innerHTML = `
                <div class="card" style="padding: 30px 20px;">
                    <div style="font-size: 60px; margin-bottom: 20px;">🕵️‍♂️</div>
                    <h1 style="margin-bottom: 10px;">لعبة برا السالفة</h1>
                    <p style="color: #a29bfe; margin-bottom: 30px; font-size: 16px;">اكتشف الجاسوس قبل فوات الأوان!</p>
                    <button onclick="navigateTo('online_menu')" style="margin-bottom: 15px;">🌐 لعب أونلاين</button>
                    <button style="background: linear-gradient(45deg, #e056fd, #be2edd);" onclick="navigateTo('setup', {step: 1})">🏠 لعب أوفلاين (مجلس)</button>
                </div>`;
        }

        // --- Online Logic ---
        let currentRoom = null;
        let isPolling = false;
        let pollTimeout = null;
        let lastRenderedHTML = "";

        function updateMainUI(html) {
            if (lastRenderedHTML === html) return;
            lastRenderedHTML = html;
            document.getElementById('main-ui').innerHTML = html;
        }

        function showToast(message, isSuccess = true) {
            let t = document.getElementById('app-toast');
            if(!t) {
                t = document.createElement('div');
                t.id = 'app-toast';
                t.className = 'toast';
                document.body.appendChild(t);
            }
            t.innerText = message;
            t.style.background = isSuccess ? 'rgba(46, 204, 113, 0.95)' : 'rgba(235, 77, 75, 0.95)';
            t.classList.add('show');
            setTimeout(() => {
                t.classList.remove('show');
            }, 2500);
        }

        function showError(message, title = "حدث خطأ ⚠️") {
            lastRenderedHTML = ""; // ريست للكاش عند عرض الأخطاء
            document.getElementById('main-ui').innerHTML = `
                <div class="card" style="border-color:var(--error); box-shadow: 0 0 20px rgba(235, 77, 75, 0.4); animation: pop 0.3s ease;">
                    <h2 style="color:var(--error); margin-bottom:15px;">${title}</h2>
                    <div style="background:rgba(235, 77, 75, 0.1); padding:15px; border-radius:15px; margin-bottom:20px; font-weight:bold; word-break:break-all; text-align:right; direction:rtl; line-height:1.6;">
                        ${message}
                    </div>
                    <button style="background:var(--primary);" onclick="showOnlineMenu()">العودة للأونلاين</button>
                </div>`;
        }

        function showOnlineMenu(push = true) {
            if(push) history.pushState({screen: 'online_menu'}, "");
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h1>اللعب أونلاين</h1>
                    <button id="btn-create-room" style="background: linear-gradient(135deg, #2ecc71, #27ae60); box-shadow: 0 4px 15px rgba(46, 204, 113, 0.4); border-radius: 20px; font-weight: 900; letter-spacing: 1px;" onclick="createRoom()">✨ إنشاء غرفة جديدة</button>
                    <div style="margin:20px 0;">
                        <input id="join_code" placeholder="رمز الغرفة (مثال: ABCD)" style="text-transform:uppercase">
                        <button onclick="joinRoom()">دخول غرفة</button>
                    </div>
                    <button style="background:#636e72" onclick="navigateTo('menu')">رجوع</button>
                </div>`;
        }

        let isCreatingRoom = false;
        async function createRoom() {
            console.log('createRoom called', { currentUser });
            if (isCreatingRoom) return;
            if (!currentUser || !currentUser.user_id) {
                showError("بيانات المستخدم غير مكتملة. يرجى تسجيل الخروج والدخول مرة أخرى.", "خطأ في بيانات الحساب");
                return;
            }

            const btn = document.getElementById('btn-create-room');
            let originalText = "";
            if (btn) {
                originalText = btn.innerText;
                btn.disabled = true;
                btn.innerText = "جاري الإنشاء...";
            }

            // عرض حالة تحميل بصرية جميلة فوراً حتى يعلم اللاعب ببدء العملية
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>جاري إنشاء الغرفة...</h2>
                    <p>يرجى الانتظار، نقوم بإعداد جلسة اللعب وسيرفر الغرفة حالياً.</p>
                    <div class="loading-spinner" style="margin: 20px auto;"></div>
                </div>`;

            isCreatingRoom = true;
            try {
                const res = await fetch('/api/online/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        user_id: currentUser.user_id.toString(), // إرسال كـ string لضمان الدقة
                        player_name: currentUser.player_name || "لاعب مجهول"
                    })
                });

                if (!res.ok) {
                    const text = await res.text();
                    console.error("Create Room failed HTTP response:", res.status, text);
                    throw new Error(`خطأ من الخادم (HTTP ${res.status}): ${text || 'تعذر الاتصال'}`);
                }

                const d = await res.json();
                console.log("Create Room response:", d);
                if (d.success && d.room_code) {
                    await enterRoom(d.room_code);
                } else {
                    showError(d.msg || "فشل السيرفر في توليد الغرفة.", "فشل إنشاء الغرفة");
                }
            } catch (err) {
                console.error("Create Room Error:", err);
                showError(err.message || "فشل الاتصال بالسيرفر. يرجى التحقق من الشبكة ومحاولة تسجيل الدخول مرة أخرى.", "خطأ تقني");
            } finally {
                isCreatingRoom = false;
            }
        }

        async function joinRoom() {
            const codeInput = document.getElementById('join_code');
            const code = codeInput.value.trim().toUpperCase();
            if(!code) return;

            if (!currentUser || !currentUser.user_id) {
                showError("بيانات المستخدم غير مكتملة. يرجى تسجيل الخروج والدخول مرة أخرى.", "خطأ في بيانات الحساب");
                return;
            }

            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>جاري الانضمام للغرفة...</h2>
                    <p>يرجى الانتظار، نتأكد من الرمز ${code}...</p>
                    <div class="loading-spinner" style="margin: 20px auto;"></div>
                </div>`;

            try {
                const res = await fetch('/api/online/join', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({room_code: code, user_id: currentUser.user_id, player_name: currentUser.player_name})
                });

                if (!res.ok) {
                    const text = await res.text();
                    throw new Error(`خطأ من الخادم (HTTP ${res.status}): ${text || 'تعذر الاتصال'}`);
                }
                const d = await res.json();
                if(d.success) {
                    await enterRoom(code);
                } else {
                    showError(d.msg || "تعذر الانضمام للغرفة. تأكد من صحة الرمز.", "فشل الانضمام");
                }
            } catch(e) {
                console.error("Join room failed", e);
                showError(e.message || "حدث خطأ غير متوقع أثناء الاتصال بالخادم. يرجى مراجعة اتصالك بالإنترنت.", "خطأ تقني");
            }
        }

        async function enterRoom(code) {
            console.log('enterRoom called', code);
            currentRoom = code;
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>جاري دخول الغرفة...</h2>
                    <p>رمز الغرفة: <b style="color:var(--accent)">${code}</b></p>
                    <div class="loading-spinner" style="margin: 20px auto;"></div>
                </div>`;
            try {
                const success = await updateRoomState();
                console.log('enterRoom updateRoomState result', success);
                if (success) {
                    startPolling();
                } else {
                    showError(`عذراً، لم نجد الغرفة المطلوبة. يرجى التأكد من أن الرمز (${code}) صحيح ولم يتم إغلاق الغرفة.`, "لم يتم العثور على الغرفة");
                }
            } catch (e) {
                console.error("Initial room entry failed:", e);
                showError(e.message || "فشل الاتصال الفوري بالسيرفر للدخول للغرفة. يرجى المحاولة لاحقاً.", "خطأ في الاتصال");
            }
        }

        function startPolling() {
            if (pollTimeout) clearTimeout(pollTimeout);
            isPolling = true;
            pollNext();
        }

        function stopPolling() {
            isPolling = false;
            if (pollTimeout) clearTimeout(pollTimeout);
        }

        async function pollNext() {
            if (!isPolling || !currentRoom) return;
            try {
                await updateRoomState();
            } catch (e) {
                console.error("Poll cycle error:", e);
            }
            if (isPolling && currentRoom) {
                pollTimeout = setTimeout(pollNext, 2000);
            }
        }

        let onlineTimerInterval = null;
        let onlineTimeLeft = 0;
        function startOnlineCountdown(timeLeft, elementId, templateFn) {
            onlineTimeLeft = timeLeft;
            const elem = document.getElementById(elementId);
            if (elem) {
                elem.innerText = templateFn(onlineTimeLeft);
                elem.setAttribute('data-val', onlineTimeLeft);
            }

            if (onlineTimerInterval) clearInterval(onlineTimerInterval);
            onlineTimerInterval = setInterval(() => {
                if (onlineTimeLeft > 0) {
                    onlineTimeLeft--;
                    const el = document.getElementById(elementId);
                    if (el) {
                        el.innerText = templateFn(onlineTimeLeft);
                        el.setAttribute('data-val', onlineTimeLeft);
                    }
                    if (onlineTimeLeft <= 5 && onlineTimeLeft > 0 && elementId === 'questions-timer') {
                        AUDIO.warning.play().catch(()=>{});
                    }
                } else {
                    clearInterval(onlineTimerInterval);
                }
            }, 1000);
        }

        let activeStatePromise = null;
        async function updateRoomState() {
            if(!currentRoom) return false;
            if (activeStatePromise) return activeStatePromise;

            activeStatePromise = (async () => {
                try {
                    console.log('updateRoomState fetching', currentRoom);
                    const res = await fetch(`/api/online/room/${currentRoom}`);
                    console.log('updateRoomState status', res.status);
                    if (!res.ok) {
                        if (res.status === 404) {
                            showError("تم إغلاق الغرفة من قبل المضيف أو انتهت جلسة اللعب.", "الغرفة غير موجودة أو مغلقة");
                            leaveRoom();
                            return false;
                        }
                        throw new Error("Room fetch failed");
                    }
                    const d = await res.json();
                    console.log('updateRoomState response', d);
                    if(d.success) {
                        window.roomData = d;
                        const status = d.room.status;

                        // Ensure exit button is visible to ALL players since they are in an active room!
                        if(document.getElementById('global-exit-btn')) {
                            document.getElementById('global-exit-btn').style.display = 'block';
                        }

                        // التحديث البصري للحالة
                        if(status === 'waiting') {
                            renderRoom();
                        } else if(status === 'voting_limit') {
                            renderVotingLimit();
                        } else if(status === 'voting_cat') {
                            renderVotingCat();
                        } else if(status === 'playing_roles') {
                            renderOnlineRoles();
                        } else if(status === 'playing_questions') {
                            renderOnlineQuestions();
                        } else if(status === 'voting_spy') {
                            renderOnlineVoting();
                        } else if(status === 'spy_reveal') {
                            renderOnlineReveal();
                        } else if(status === 'result') {
                            renderOnlineResult();
                        }

                        // التنبيهات الصوتية
                        if (status !== lastKnownStatus) {
                            if (status === 'playing_questions') AUDIO.tick.play().catch(()=>{});
                            if (status === 'result' && d.room.game_data.game_over) AUDIO.success.play().catch(()=>{});
                            lastKnownStatus = status;
                        }

                        // الكروت والعقوبات
                        d.players.forEach(p => {
                            const oldCards = lastKnownCards[p.user_id] || {yellow: 0, red: false};
                            if (p.yellow_cards > oldCards.yellow || (p.red_card && !oldCards.red)) {
                                AUDIO.penalty.play().catch(()=>{});
                            }
                            lastKnownCards[p.user_id] = {yellow: p.yellow_cards, red: p.red_card};
                        });

                        return true;
                    } else {
                        return false;
                    }
                } catch (err) {
                    console.error("Update room state error:", err);
                    return false;
                } finally {
                    activeStatePromise = null;
                }
            })();
            return activeStatePromise;
        }

        function renderVotingLimit() {
            const {room, players} = window.roomData;
            const myVote = players.find(p => p.user_id == currentUser.user_id)?.vote_limit;
            
            const timeLeft = room.time_left ?? 0;

            const limitCard = document.getElementById('voting-limit-card');
            if (limitCard) {
                const buttons = limitCard.querySelectorAll('.win-opt');
                buttons.forEach(btn => {
                    const val = parseInt(btn.getAttribute('data-value'));
                    const isSelected = myVote == val;
                    if (isSelected) btn.classList.add('selected'); else btn.classList.remove('selected');
                });
                startOnlineCountdown(timeLeft, 'voting-limit-timer', (t) => `⏱️ الوقت المتبقي للتصويت: ${t} ثانية`);
                return;
            }

            let h = `<h2>🏆 هدف الفوز</h2>
                     <p style="color: #9aa0b4; margin-bottom: 20px;">أول لاعب يصل لهذا العدد من النقاط يفوز</p>
                     <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin:20px 0;">`;
            [5, 10, 15, 20].forEach(val => {
                const isSelected = myVote == val;
                h += `<div class="win-opt ${isSelected?'selected':''}" data-value="${val}" onclick="sendVote('limit', ${val})">
                        ${val} نقطة
                      </div>`;
            });
            h += `</div>
                  <div id="voting-limit-timer" style="margin-top:20px; color:var(--error); font-weight:bold; font-size:18px;">⏱️ الوقت المتبقي: ${timeLeft} ثانية</div>`;
            updateMainUI(`<div class="card" id="voting-limit-card">${h}</div>`);
            startOnlineCountdown(timeLeft, 'voting-limit-timer', (t) => `⏱️ الوقت المتبقي: ${t} ثانية`);
        }

        function renderVotingCat() {
            const {room, players} = window.roomData;
            const myVote = players.find(p => p.user_id == currentUser.user_id)?.vote_cat;
            
            const timeLeft = room.time_left ?? 0;

            const catCard = document.getElementById('voting-cat-card');
            if (catCard) {
                const items = catCard.querySelectorAll('.vote-item');
                items.forEach(btn => {
                    const cat = btn.getAttribute('data-value');
                    const isSelected = myVote == cat;
                    btn.style.background = isSelected ? 'var(--success)' : '';
                    btn.innerHTML = `${cat} ${isSelected ? '✅' : ''}`;
                });
                startOnlineCountdown(timeLeft, 'voting-cat-timer', (t) => `⏱️ الوقت المتبقي للتصويت: ${t} ثانية`);
                return;
            }

            let h = `<h2>📂 اختر الفئة</h2>
                     <p style="color: #9aa0b4; margin-bottom: 10px;">سيتم اختيار الفئة الأكثر تصويتاً</p>
                     <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin:20px 0; max-height:350px; overflow-y:auto; padding:5px; border: 1px solid rgba(255,255,255,0.05); border-radius:15px; background: rgba(0,0,0,0.2);">`;
            ["أكلات", "حيوانات", "ملابس", "كورة", "سيارات", "شركات", "كواكب", "أجهزة", "تطبيقات", "فواكه وخضار", "شخصيات", "كارتون", "مشروبات", "حلويات", "مسلسلات", "انمي", "كيبوب", "قيمرز", "مهن"].forEach(cat => {
                const isSelected = myVote == cat;
                h += `<div class="vote-item" data-value="${cat}" onclick="sendVote('cat', '${cat}')" style="background:${isSelected ? 'var(--success)' : ''}; font-size:15px; padding:12px; margin:0;">
                        ${cat} ${isSelected ? '✅' : ''}
                      </div>`;
            });
            h += `</div>
                  <div id="voting-cat-timer" style="margin-top:10px; color:var(--error); font-weight:bold; font-size:18px;">⏱️ الوقت المتبقي: ${timeLeft} ثانية</div>`;
            updateMainUI(`<div class="card" id="voting-cat-card">${h}</div>`);
            startOnlineCountdown(timeLeft, 'voting-cat-timer', (t) => `⏱️ الوقت المتبقي للتصويت: ${t} ثانية`);
        }

        let isSendingVote = false;
        async function sendVote(type, value) {
            if (isSendingVote) return;
            isSendingVote = true;

            const buttons = document.querySelectorAll('.card button');
            buttons.forEach(b => b.style.opacity = '0.5');

            try {
                const res = await fetch('/api/online/submit_vote', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({room_code: currentRoom, user_id: currentUser.user_id, type: type, value: value})
                });
                if (!res.ok) throw new Error('Network response was not ok');
                const d = await res.json();
                if(!d.success) {
                    showError(d.msg || "تعذر إرسال التصويت", "فشل التصويت");
                }
            } catch (e) {
                console.error(e);
                showError("حدث خطأ في الاتصال بالسيرفر أثناء إرسال التصويت.", "خطأ في الاتصال");
            } finally {
                isSendingVote = false;
                buttons.forEach(b => b.style.opacity = '1');
            }
            await updateRoomState();
        }

        function renderRoom() {
            if(!window.roomData) {
                document.getElementById('main-ui').innerHTML = `<div class="card">جاري التحميل...</div>`;
                return;
            }
            const {room, players} = window.roomData;
            let pList = players.map(p => {
                let cards = "";
                if(p.red_card) cards = " 🟥";
                else if(p.yellow_cards > 0) cards = " " + "🟨".repeat(p.yellow_cards);
                return `<div class="score-item"><span>${p.player_name}${cards}</span> ${p.is_ready ? '✅' : '⏳'}</div>`;
            }).join('');

            // التحقق مما إذا كانت بطاقة الانتظار معروضة بالفعل لتحديث قائمة اللاعبين فقط وتفادي النبض/الرمش
            const lobbyCard = document.getElementById('lobby-card');
            if (lobbyCard && currentRoom && currentRoom.trim().toUpperCase() === room.room_code.trim().toUpperCase()) {
                const pListContainer = document.getElementById('lobby-players-list');
                if (pListContainer && pListContainer.innerHTML !== pList) {
                    pListContainer.innerHTML = pList;
                }
                return;
            }

            document.getElementById('main-ui').innerHTML = `
                <div class="card" id="lobby-card">
                    <h2>رمز الغرفة</h2>
                    <span id="lobby-room-code" style="color:var(--accent); font-size:38px; font-weight:900; letter-spacing:2px; display:block; margin:10px 0;">${room.room_code}</span>
                    <div style="display:flex; gap:10px; justify-content:center; margin-bottom:20px;">
                        <button style="background:var(--accent); color:var(--card); font-size:14px; padding:10px 15px; margin:0;" onclick="copyRoomCode()">📋 نسخ الرمز</button>
                        <button style="background:var(--primary); font-size:14px; padding:10px 15px; margin:0;" onclick="copyInviteLink()">🔗 نسخ الرابط</button>
                    </div>
                    <div id="lobby-players-list" style="margin:10px 0; text-align:right;">${pList}</div>
                    ${room.host_id == currentUser.user_id ? `
                        <button onclick="startOnlineGame()">بدء اللعبة</button>` :
                        '<p>بانتظار المضيف لبدء اللعبة...</p>'}
                    <button style="background:#636e72" onclick="leaveRoom()">خروج</button>
                </div>`;
        }

        function copyInviteLink() {
            const url = window.location.origin + '?join=' + currentRoom;
            navigator.clipboard.writeText(url).then(() => {
                showToast("🔗 تم نسخ رابط الدعوة! أرسله لأصدقائك.");
            });
        }

        function copyRoomCode() {
            if (!currentRoom) return;
            navigator.clipboard.writeText(currentRoom).then(() => {
                showToast("📋 تم نسخ رمز الغرفة: " + currentRoom);
            }).catch(err => {
                console.error("Failed to copy code: ", err);
                const tempInput = document.createElement("input");
                tempInput.value = currentRoom;
                document.body.appendChild(tempInput);
                tempInput.select();
                document.execCommand("copy");
                document.body.removeChild(tempInput);
                showToast("📋 تم نسخ رمز الغرفة: " + currentRoom);
            });
        }

        async function joinRoomByCode(code) {
            const res = await fetch('/api/online/join', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({room_code: code, user_id: currentUser.user_id, player_name: currentUser.player_name})
            });
            const d = await res.json();
            if(d.success) enterRoom(code); else showError(d.msg || "تعذر الانضمام للغرفة.", "فشل الانضمام");
        }

        async function startOnlineGame() {
            if(document.getElementById('global-exit-btn')) document.getElementById('global-exit-btn').style.display = 'block';
            try {
                const res = await fetch('/api/online/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({room_code: currentRoom, user_id: currentUser.user_id})
                });
                if (!res.ok) throw new Error('Network response was not ok');
                const d = await res.json();
                if(!d.success) showError(d.msg || "تعذر بدء اللعبة", "خطأ في بدء اللعبة");
            } catch (e) {
                console.error(e);
                showError("حدث خطأ في الاتصال بالسيرفر أثناء بدء اللعبة.", "خطأ في الاتصال");
            }
        }

        function renderOnlineRoles() {
            const {room, players} = window.roomData;
            const me = players.find(p => p.user_id == currentUser.user_id);
            const isSpy = room.spy_id == currentUser.user_id;

            if(me.is_ready) {
                updateMainUI(`<div class="card"><h3>بانتظار بقية اللاعبين...</h3><div class="shuffling">⏳</div></div>`);
                return;
            }

            updateMainUI(`
                <div class="card">
                    <h3>أنت: <b style="color:var(--accent)">${currentUser.player_name}</b></h3>
                    <div id="box" style="background:#0f0c29; padding:20px; border-radius:20px; margin:20px 0;">
                        <h3>${isSpy ? '🕵️ أنت برة السالفة!' : '🤫 السالفة هي: ' + room.secret_word}</h3>
                    </div>
                    <button onclick="onlineAction('ready_role')">فهمت، جاهز</button>
                </div>`);
        }

        async function onlineAction(action, extra = {}) {
            try {
                const res = await fetch('/api/online/action', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({room_code: currentRoom, user_id: currentUser.user_id, action, ...extra})
                });
                if (!res.ok) throw new Error('Network response was not ok');
                const d = await res.json();
                if(!d.success && d.msg) showError(d.msg, "تنبيه ⚠️");
            } catch (e) {
                console.error(e);
                showError("حدث خطأ أثناء تنفيذ هذا الإجراء بالسيرفر.", "خطأ في الاتصال");
            }
            updateRoomState();
        }

        function escapeHtml(text) {
            if (!text) return "";
            return text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        function buildQAChatHistory() {
            if (!window.roomData || !window.roomData.room || !window.roomData.room.game_data) return "";
            const q_seq = window.roomData.room.game_data.q_seq || [];
            const completed = q_seq.filter(q => q.status === 'done');
            if (completed.length === 0) return "";

            let chatHtml = `<div class="qa-chat-container">
                <div class="qa-chat-header">💬 سجل الأسئلة والأجوبة السابقة</div>
                <div class="qa-chat-body" id="qa-compact-chat-scroll" style="max-height:160px; overflow-y:auto; display:flex; flex-direction:column; gap:10px; padding:10px;">`;
            
            completed.forEach(q => {
                chatHtml += `
                    <div class="chat-message-group">
                        <div class="chat-bubble bubble-asker" style="font-size:13px; padding:8px 12px; border-radius:12px; width:fit-content; max-width:85%;">
                            <div class="bubble-sender">🙋‍♂️ ${q.asker_name}</div>
                            <div class="bubble-content">${escapeHtml(q.question)}</div>
                        </div>
                        <div class="chat-bubble bubble-answerer" style="font-size:13px; padding:8px 12px; border-radius:12px; width:fit-content; max-width:85%; align-self:flex-end;">
                            <div class="bubble-sender">💬 ${q.ans_name}</div>
                            <div class="bubble-content">${escapeHtml(q.answer)}</div>
                        </div>
                    </div>`;
            });
            
            chatHtml += `</div></div>`;
            setTimeout(() => {
                const compactScroll = document.getElementById('qa-compact-chat-scroll');
                if (compactScroll) compactScroll.scrollTop = compactScroll.scrollHeight;
            }, 50);
            return chatHtml;
        }

        function renderOnlineQuestions() {
            if(!window.roomData || !window.roomData.room.game_data) return;
            const {room, players} = window.roomData;
            const gameData = room.game_data;
            const q_idx = gameData.q_idx || 0;
            const q_seq = gameData.q_seq || [];
            if(q_idx >= q_seq.length) return;
            const q = q_seq[q_idx];

            const isAsker = q.asker_id == currentUser.user_id;
            const isAnswerer = q.ans_id == currentUser.user_id;
            const me = players.find(p => p.user_id == currentUser.user_id);

            const timeLeft = room.time_left ?? 0;
            const stateKey = `${q_idx}_${q.status}_${me.red_card ? 'red' : 'active'}`;

            // Check if we need to full-render or just partial update
            const questionsCard = document.getElementById('questions-card');

            // Build chat bubbles HTML
            let chatHtml = "";
            q_seq.forEach((item, idx) => {
                if (item.status === 'done') {
                    chatHtml += `
                        <div class="chat-message-group">
                            <div class="chat-bubble bubble-asker">
                                <div class="bubble-sender">🙋‍♂️ ${item.asker_name}:</div>
                                <div class="bubble-content">${escapeHtml(item.question)}</div>
                            </div>
                            <div class="chat-bubble bubble-answerer">
                                <div class="bubble-sender">💬 ${item.ans_name}:</div>
                                <div class="bubble-content">${escapeHtml(item.answer)}</div>
                            </div>
                        </div>`;
                } else if (idx === q_idx) {
                    if (item.status === 'answering') {
                        chatHtml += `
                            <div class="chat-message-group">
                                <div class="chat-bubble bubble-asker">
                                    <div class="bubble-sender">🙋‍♂️ ${item.asker_name}:</div>
                                    <div class="bubble-content">${escapeHtml(item.question)}</div>
                                </div>
                                <div class="chat-bubble bubble-typing">
                                    <div class="bubble-sender">💬 ${item.ans_name}:</div>
                                    <div class="bubble-content">جاري كتابة الإجابة... <span class="typing-dots"></span></div>
                                </div>
                            </div>`;
                    } else if (item.status === 'pending' || item.status === 'asking') {
                        chatHtml += `
                            <div class="chat-message-group">
                                <div class="chat-bubble bubble-typing">
                                    <div class="bubble-sender">🙋‍♂️ ${item.asker_name}:</div>
                                    <div class="bubble-content">جاري كتابة السؤال... <span class="typing-dots"></span></div>
                                </div>
                            </div>`;
                    }
                }
            });

            if (questionsCard && questionsCard.getAttribute('data-state-key') === stateKey) {
                // PARTIAL UPDATE: Just update the chat scroll area if content changed
                const scrollArea = document.getElementById('qa-chat-scroll');
                if (scrollArea && scrollArea.getAttribute('data-content-hash') !== chatHtml.length.toString()) {
                    scrollArea.innerHTML = chatHtml || '<p style="text-align:center; color:#9aa0b4; margin-top:20px;">لا توجد أسئلة سابقة بعد. الجولة تبدأ الآن!</p>';
                    scrollArea.setAttribute('data-content-hash', chatHtml.length.toString());
                    scrollArea.scrollTop = scrollArea.scrollHeight;
                }
                // Update timer
                const timerElem = document.getElementById('questions-timer');
                if (timerElem) {
                   // We trust the local countdown but sync with server if drift is large
                   const localVal = parseInt(timerElem.getAttribute('data-val') || "0");
                   if (Math.abs(localVal - timeLeft) > 2) {
                       startOnlineCountdown(timeLeft, 'questions-timer', (t) => `⏱️ الوقت المتبقي: ${t} ثانية`);
                   }
                }
                return;
            }

            // FULL RENDER (State changed)
            let inputHtml = "";
            if (me.red_card) {
                inputHtml = `<div class="qa-typing-status" style="color:var(--error); font-weight:bold;">❌ أنت مستبعد من هذه الجولة (كرت أحمر)</div>`;
            } else if (q.status === 'pending' || q.status === 'asking') {
                if (isAsker) {
                    inputHtml = `
                        <div style="display: flex; gap: 8px;">
                            <input id="online_q_input" placeholder="اكتب سؤالك لـ ${q.ans_name}..." style="margin: 0; flex-grow: 1;">
                            <button onclick="submitOnlineQuestion()" style="margin: 0; width: auto; padding: 12px 20px;">إرسال 🚀</button>
                        </div>`;
                } else {
                    inputHtml = `<div class="qa-typing-status">⏳ بانتظار <b style="color:var(--accent)">${q.asker_name}</b> ليكتب السؤال...</div>`;
                }
            } else if (q.status === 'answering') {
                if (isAnswerer) {
                    inputHtml = `
                        <div style="display: flex; gap: 8px;">
                            <input id="online_a_input" placeholder="اكتب إجابتك هنا..." style="margin: 0; flex-grow: 1;">
                            <button onclick="submitOnlineAnswer()" style="margin: 0; width: auto; padding: 12px 20px;">إرسال 🚀</button>
                        </div>`;
                } else {
                    inputHtml = `<div class="qa-typing-status">⏳ بانتظار <b style="color:var(--accent)">${q.ans_name}</b> ليرد على السؤال...</div>`;
                }
            }

            let fullHtml = `
                <div class="qa-chat-layout">
                    <!-- Header -->
                    <div class="qa-chat-header-main">
                        <h2>💬 مرحلة الأسئلة والدردشة</h2>
                        <div class="qa-current-turn">
                            <span style="color: var(--primary); font-weight: bold;">${q.asker_name}</span> 
                            👈 
                            <span style="color: var(--error); font-weight: bold;">${q.ans_name}</span>
                        </div>
                    </div>
                    
                    <!-- Chat Scroll -->
                    <div class="qa-chat-scroll-area" id="qa-chat-scroll" data-content-hash="${chatHtml.length}">
                        ${chatHtml || '<p style="text-align:center; color:#9aa0b4; margin-top:20px;">لا توجد أسئلة سابقة بعد. الجولة تبدأ الآن!</p>'}
                    </div>
                    
                    <!-- Footer Input Area -->
                    <div class="qa-chat-footer-input">
                        <div id="questions-timer" class="qa-timer-badge">⏱️ الوقت المتبقي: ${timeLeft} ثانية</div>
                        <div class="qa-input-box-wrapper">
                            ${inputHtml}
                        </div>
                    </div>
                </div>
            `;

            updateMainUI(`<div class="card" id="questions-card" data-state-key="${stateKey}" style="padding: 15px; border-radius: 20px;">${fullHtml}</div>`);
            
            // Auto scroll to bottom
            setTimeout(() => {
                const scrollArea = document.getElementById('qa-chat-scroll');
                if (scrollArea) {
                    scrollArea.scrollTop = scrollArea.scrollHeight;
                }
            }, 50);

            // Start countdown
            startOnlineCountdown(timeLeft, 'questions-timer', (t) => `⏱️ الوقت المتبقي: ${t} ثانية`);
        }

        async function submitOnlineQuestion() {
            const text = document.getElementById('online_q_input').value.trim();
            if(!text) return;
            await onlineAction('submit_question', {text});
        }
        async function submitOnlineAnswer() {
            const text = document.getElementById('online_a_input').value.trim();
            if(!text) return;
            await onlineAction('submit_answer', {text});
        }

        function renderOnlineVoting() {
            const {room, players} = window.roomData;
            const me = players.find(p => p.user_id == currentUser.user_id);

            const timeLeft = room.time_left ?? 0;

            if(me.red_card) {
                updateMainUI(`<div class="card"><h3>أنت مستبعد من التصويت (كرت أحمر)</h3><p>بانتظار بقية اللاعبين...</p><div class="shuffling">⏳</div></div>`);
                return;
            }

            if(me.is_ready) {
                updateMainUI(`<div class="card"><h3>تم إرسال صوتك...</h3><p>بانتظار بقية اللاعبين...</p><div class="shuffling">⏳</div></div>`);
                return;
            }

            const votingCard = document.getElementById('online-voting-card');
            if (votingCard) {
                startOnlineCountdown(timeLeft, 'online-voting-timer', (t) => `⏱️ الوقت المتبقي للتصويت: ${t} ثانية`);
                return;
            }

            let h = `<h3>صوت سراً: منو اللي برة السالفة؟</h3>
                     <div id="vbox" style="display:flex; flex-direction:column; gap:10px; margin-top:20px;">`;
            players.forEach(p => {
                if(p.user_id != currentUser.user_id) {
                    h += `<button class="vote-item" onclick="onlineAction('vote', {target_id: ${p.user_id}})">
                            ${p.player_name} ${p.red_card ? ' (مستبعد)' : ''}
                          </button>`;
                }
            });
            h += `</div>
                  <div id="online-voting-timer" style="margin-top:20px; color:var(--error); font-weight:bold; font-size:18px;">⏱️ الوقت المتبقي للتصويت: ${timeLeft} ثانية</div>`;
            h += buildQAChatHistory();
            updateMainUI(`<div class="card" id="online-voting-card">${h}</div>`);
            startOnlineCountdown(timeLeft, 'online-voting-timer', (t) => `⏱️ الوقت المتبقي للتصويت: ${t} ثانية`);
        }

        function renderOnlineReveal() {
            const {room, players} = window.roomData;
            const isSpy = room.spy_id == currentUser.user_id;
            const spy = players.find(p => p.user_id == room.spy_id);

            if(isSpy) {
                let h = `<h3>كشفوك! خمن وش السالفة؟</h3>`;
                room.game_data.guesses.forEach(g => {
                    h += `<div class="vote-item" onclick="onlineAction('spy_guess', {guess: '${g.replace(/'/g, "\\'")}'})">${g}</div>`;
                });
                h += buildQAChatHistory();
                updateMainUI(`<div class="card">${h}</div>`);
            } else {
                let h = `
                        <h1>اللي برة السالفة هو:</h1>
                        <h2 style="color:var(--error); font-size:40px;">${spy.player_name}</h2>
                        <p>بانتظار تخمين الجاسوس...</p>
                        <div class="shuffling">🌀</div>`;
                h += buildQAChatHistory();
                updateMainUI(`<div class="card">${h}</div>`);
            }
        }

        function renderOnlineResult() {
            const {room, players} = window.roomData;
            const spy = players.find(p => p.user_id == room.spy_id);
            const spyGuessedRight = (room.game_data.spy_guess === room.secret_word);
            const isHost = room.host_id == currentUser.user_id;
            const gameOver = room.game_data.game_over;
            const winner = players.find(p => p.user_id == room.game_data.winner_id);

            let scoresList = "";
            [...players].sort((a,b) => b.score - a.score).forEach(p => {
                let cards = "";
                if(p.red_card) cards = " 🟥";
                else if(p.yellow_cards > 0) cards = " " + "🟨".repeat(p.yellow_cards);
                scoresList += `<div class="score-item"><span>${p.player_name}${cards}</span> <b>${p.score}</b></div>`;
            });

            updateMainUI(`
                <div class="card">
                    ${gameOver ? `<h1 style="color:var(--accent)">🏆 الفائز باللعبة: ${winner ? winner.player_name : 'غير معروف'}</h1>` : ''}
                    <h2 style="color:${spyGuessedRight? 'var(--success)':'var(--error)'}">السالفة كانت: ${room.secret_word}</h2>
                    <p>${spy.player_name} ${spyGuessedRight ? 'عرف السالفة!' : 'ما عرف السالفة.'}</p>
                    <hr style="border:1px solid #3c339e; margin:15px 0;">
                    <h3>النقاط الحالية (الهدف: ${room.win_limit}):</h3>
                    <div style="margin-bottom:20px;">${scoresList}</div>
                    ${gameOver ?
                        `<button onclick="showMenu()">العودة للقائمة الرئيسية</button>` :
                        (isHost ? `<button onclick="onlineAction('new_round')">جولة جديدة</button>` : `<p>بانتظار المضيف لبدء جولة جديدة...</p>`)
                    }
                    <button style="background:#636e72" onclick="leaveRoom()">خروج من الغرفة</button>
                </div>`);
        }

        async function leaveRoom() {
            if(document.getElementById('global-exit-btn')) document.getElementById('global-exit-btn').style.display = 'none';
            stopPolling();
            if (currentRoom && currentUser) {
                try {
                    await fetch('/api/online/leave', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({room_code: currentRoom, user_id: currentUser.user_id})
                    });
                } catch(e) {
                    console.error("Failed to leave room endpoint:", e);
                }
            }
            currentRoom = null;
            showMenu();
        }

        function showEditProfile(push = true) {
            if(push) {
                history.pushState({screen: 'edit_profile'}, "");
                toggleSidebar();
            }
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>تعديل بياناتي</h2>
                    <input id="edit_u" value="${currentUser.username_key}">
                    <input id="edit_n" value="${currentUser.player_name}">
                    <input id="edit_p" type="password" value="${currentUser.password_key}">
                    <button onclick="updateProfile()">حفظ التعديلات</button>
                    <button style="background:#636e72" onclick="navigateTo('menu')">إلغاء</button>
                </div>`;
        }

        async function updateProfile() {
            const res = await fetch('/api/auth/update', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({old_username: currentUser.username_key, username: edit_u.value, password: edit_p.value, name: edit_n.value})});
            const d = await res.json();
            if(d.success) { alert("تم التحديث! سجل دخولك مجدداً"); logout(); } else alert(d.msg);
        }

        function changePCount(delta) {
            let val = parseInt(localStorage.getItem('pCount') || 3) + delta;
            if(val >= 3 && val <= 20) {
                localStorage.setItem('pCount', val);

                let inp = document.getElementById('p_count');
                if(inp) inp.value = val;

                const reqEl = document.getElementById('required_n_display');
                if(reqEl) reqEl.innerText = val;

                const reqSum = document.getElementById('required_n_summary');
                if(reqSum) reqSum.innerText = val;

                updateSelectedCount();
            }
        }
        function saveAndNext(btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="shuffling" style="font-size:20px; margin:0;">🌀</span> جاري التحميل...';
            localStorage.setItem('pCount', document.getElementById('p_count').value);
            setTimeout(() => navigateTo('setup', {step: 2}), 500);
        }

        function togglePSelection(el, name) {
            const icon = el.querySelector('.status-icon');
            if(icon.innerText === '✅') {
                icon.innerText = '⬜';
            } else {
                const targetN = parseInt(localStorage.getItem('pCount') || 3);
                const currentCount = Array.from(document.querySelectorAll('.status-icon')).filter(i => i.innerText === '✅').length;
                if(currentCount >= targetN) {
                    alert("لقد اخترت العدد المطلوب فعلاً (" + targetN + ") لاعبين");
                    return;
                }
                icon.innerText = '✅';
            }
            updateSelectedCount();
        }

        function updateSelectedCount() {
            const count = Array.from(document.querySelectorAll('.status-icon')).filter(i => i.innerText === '✅').length;
            const counterEl = document.getElementById('selected_count');
            if(counterEl) counterEl.innerText = count;

            const nextBtn = document.querySelector('button[onclick="confirmPlayersAndNext()"]');
            if(nextBtn) {
                const targetN = parseInt(localStorage.getItem('pCount') || 3);
                nextBtn.disabled = (count !== targetN);
                nextBtn.style.opacity = (count === targetN) ? "1" : "0.5";
            }
        }

        function addNewPlayerToList() {
            const nameInp = document.getElementById('new_p_name');
            const name = nameInp.value.trim();
            if(!name) return;

            if(!currentUser.saved_players) currentUser.saved_players = [];

            // البحث عن اللاعب إذا كان موجوداً مسبقاً
            const existingIdx = currentUser.saved_players.findIndex(p => {
                const pName = (typeof p === 'string' ? p : p.name).trim();
                return pName.toLowerCase() === name.toLowerCase();
            });

            if(existingIdx !== -1) {
                const items = document.querySelectorAll('#p_selection_list .score-item');
                for(let item of items) {
                    const spanName = item.querySelector('span').innerText.trim();
                    if(spanName.toLowerCase() === name.toLowerCase()) {
                        item.scrollIntoView({behavior: 'smooth', block: 'center'});
                        item.style.transition = "all 0.3s";
                        item.style.background = "rgba(162, 155, 254, 0.5)";
                        item.style.transform = "scale(1.05)";

                        const icon = item.querySelector('.status-icon');
                        if(icon.innerText === '⬜') {
                            togglePSelection(item, spanName);
                        }

                        setTimeout(() => {
                            item.style.background = "";
                            item.style.transform = "";
                        }, 2000);

                        nameInp.value = "";
                        return;
                    }
                }
            }

            // إضافة لاعب جديد
            currentUser.saved_players.push({name: name, wins: 0});
            localStorage.setItem('user', JSON.stringify(currentUser));
            showSetup(2, false); // تحديث الواجهة فوراً دون إضافة للسجل

            // حفظ في الخلفية
            fetch('/api/user/save_players', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: currentUser.user_id, players: currentUser.saved_players})
            });
        }

        function confirmPlayersAndNext(btn) {
            const targetN = parseInt(localStorage.getItem('pCount'));
            const selected = Array.from(document.querySelectorAll('#p_selection_list .score-item'))
                .filter(el => el.querySelector('.status-icon').innerText === '✅')
                .map(el => el.querySelector('span').innerText);

            if(selected.length !== targetN) {
                if(confirm(`لقد اخترت ${selected.length} لاعبين، والمطلوب ${targetN}. هل تريد تغيير عدد اللاعبين إلى ${selected.length} والبدء؟`)) {
                    localStorage.setItem('pCount', selected.length);
                } else {
                    return;
                }
            }
            if(btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="shuffling" style="font-size:20px; margin:0;">🌀</span> جاري التحميل...';
            }
            window.pNamesSave = selected;
            setTimeout(() => navigateTo('setup', {step: 3}), 500);
        }

        async function showSetup(step, push = true) {
            if(push) history.pushState({screen: 'setup', step}, "");
            if(step === 1) {
                let savedCount = localStorage.getItem('pCount') || 3;
                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2>عدد اللاعبين</h2>
                        <div style="display: flex; align-items: center; justify-content: center; gap: 15px; margin: 20px 0;">
                            <button onclick="changePCount(-1)" style="width: 60px; margin:0; background:var(--error); font-size: 24px;">-</button>
                            <input type="number" id="p_count" value="${savedCount}" min="3" style="text-align: center; width: 100px; margin:0; font-size: 24px; font-weight: bold;">
                            <button onclick="changePCount(1)" style="width: 60px; margin:0; background:var(--success); font-size: 24px;">+</button>
                        </div>
                        <button class="btn-yellow" onclick="saveAndNext(this)">التالي</button>
                        <button style="background:#636e72" onclick="navigateTo('menu')">رجوع</button>
                    </div>`;
            } else if(step === 2) {
                const targetN = Math.max(3, parseInt(localStorage.getItem('pCount') || 3));
                let savedPlayers = currentUser.saved_players || [];

                let h = `<div id="p_selection_list" style="max-height: 300px; overflow-y: auto; margin-bottom: 20px; text-align: right;">`;

                // عرض اللاعبين المخزنين أولاً مع خاصية الاختيار
                savedPlayers.forEach((p, idx) => {
                    const name = typeof p === 'string' ? p : p.name;
                    const isSelected = idx < targetN;
                    h += `
                        <div class="score-item" style="cursor:pointer" onclick="togglePSelection(this, '${name.replace(/'/g, "\\'")}')">
                            <span>${name}</span>
                            <span class="status-icon">${isSelected ? '✅' : '⬜'}</span>
                        </div>`;
                });
                h += `</div>`;

                // حقل لإضافة لاعب جديد للقائمة
                h += `
                    <div style="display:flex; gap:10px; margin-bottom:15px;">
                        <input id="new_p_name" placeholder="اسم لاعب جديد" style="margin:0">
                        <button onclick="addNewPlayerToList()" style="width:80px; margin:0; background:var(--success)">+</button>
                    </div>

                    <div style="display: flex; align-items: center; justify-content: center; gap: 15px; margin: 15px 0; background: rgba(0,0,0,0.2); padding: 12px; border-radius: 20px; border: 1px solid #3c339e;">
                        <button onclick="changePCount(-1)" style="width: 45px; height: 45px; margin:0; background:var(--error); font-size: 24px; display:flex; align-items:center; justify-content:center;">-</button>
                        <div style="text-align: center; min-width: 100px;">
                            <span style="display:block; font-size:12px; color:#aaa;">العدد المطلوب</span>
                            <span id="required_n_display" style="font-size: 28px; font-weight: 900; color:var(--accent);">${targetN}</span>
                        </div>
                        <button onclick="changePCount(1)" style="width: 45px; height: 45px; margin:0; background:var(--success); font-size: 24px; display:flex; align-items:center; justify-content:center;">+</button>
                    </div>

                    <p id="selection_info" style="margin:10px 0; font-size:16px; color:white;">
                        المختار: <span id="selected_count" style="color:var(--success); font-weight:bold;">0</span>
                        من أصل
                        <span id="required_n_summary" style="font-weight:bold;">${targetN}</span> لاعبين
                    </p>
                    <button class="btn-yellow" onclick="confirmPlayersAndNext(this)">التالي</button>`;

                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2>اختر اللاعبين</h2>
                        ${h}
                    </div>`;

                // تحديث العداد الأولي
                updateSelectedCount();
            } else if(step === 3) {
                const cachedCats = getCachedCategories();
                if (cachedCats && cachedCats.length) {
                    await renderCategorySelection(cachedCats, true);
                    prefetchCategoryImages(cachedCats);
                } else {
                    const defaultCats = DEFAULT_CATEGORIES.map(name => ({ name }));
                    await renderCategorySelection(defaultCats, false, true);
                }

                try {
                    const res = await fetch('/api/categories');
                    if (res.ok) {
                        const cats = await res.json();
                        if (cats && cats.length) {
                            saveCachedCategories(cats);
                            await renderCategorySelection(cats);
                            prefetchCategoryImages(cats);
                        } else if (!cachedCats || !cachedCats.length) {
                            showCategoryError();
                        }
                    } else if (!cachedCats || !cachedCats.length) {
                        showCategoryError();
                    }
                } catch (err) {
                    console.error('Category fetch failed', err);
                    if (!cachedCats || !cachedCats.length) {
                        showCategoryError();
                    }
                }
            }
        }

        function selectWinLimit(el, val) {
            document.querySelectorAll('.win-opt').forEach(opt => opt.classList.remove('selected'));
            el.classList.add('selected');
            document.getElementById('win_limit_val').value = val;
        }

        function selectCat(el, name) {
            document.querySelectorAll('.cat-card').forEach(c => c.classList.remove('selected'));
            el.classList.add('selected');
            document.getElementById('selected_cat').value = name;
        }

        const THUMB_DB_NAME = 'alsalfa-thumbnails-v1';
        const THUMB_STORE_NAME = 'thumbnails';

        function getCachedCategories() {
            try {
                return JSON.parse(localStorage.getItem('cachedCategories') || '[]');
            } catch (err) {
                return [];
            }
        }

        function saveCachedCategories(cats) {
            try {
                localStorage.setItem('cachedCategories', JSON.stringify(cats));
            } catch (err) {
                console.warn('Unable to save categories cache', err);
            }
        }

        function openThumbnailDB() {
            return new Promise((resolve, reject) => {
                if (!('indexedDB' in window)) return reject(new Error('IndexedDB not supported'));
                const request = indexedDB.open(THUMB_DB_NAME, 1);
                request.onupgradeneeded = () => {
                    const db = request.result;
                    if (!db.objectStoreNames.contains(THUMB_STORE_NAME)) {
                        db.createObjectStore(THUMB_STORE_NAME);
                    }
                };
                request.onsuccess = () => resolve(request.result);
                request.onerror = () => reject(request.error);
            });
        }

        function getCachedCategoryThumbnails() {
            if (!('indexedDB' in window)) {
                try {
                    return Promise.resolve(JSON.parse(localStorage.getItem('cachedCategoryThumbnails') || '{}'));
                } catch (err) {
                    return Promise.resolve({});
                }
            }
            return openThumbnailDB().then(db => new Promise((resolve, reject) => {
                const tx = db.transaction(THUMB_STORE_NAME, 'readonly');
                const store = tx.objectStore(THUMB_STORE_NAME);
                const request = store.openCursor();
                const result = {};
                request.onsuccess = (event) => {
                    const cursor = event.target.result;
                    if (cursor) {
                        result[cursor.key] = cursor.value;
                        cursor.continue();
                    } else {
                        resolve(result);
                    }
                };
                request.onerror = () => reject(request.error);
            })).catch(() => {
                try {
                    return JSON.parse(localStorage.getItem('cachedCategoryThumbnails') || '{}');
                } catch (err) {
                    return {};
                }
            });
        }

        function saveCachedCategoryThumbnail(name, dataUrl) {
            if (!name || !dataUrl) return;
            if (!('indexedDB' in window)) {
                try {
                    const thumbs = JSON.parse(localStorage.getItem('cachedCategoryThumbnails') || '{}');
                    thumbs[name] = dataUrl;
                    localStorage.setItem('cachedCategoryThumbnails', JSON.stringify(thumbs));
                } catch (err) {
                    console.warn('Unable to save category thumbnail', err);
                }
                return;
            }
            openThumbnailDB().then(db => {
                const tx = db.transaction(THUMB_STORE_NAME, 'readwrite');
                const store = tx.objectStore(THUMB_STORE_NAME);
                store.put(dataUrl, name);
                tx.oncomplete = () => db.close();
                tx.onerror = () => db.close();
            }).catch(err => {
                console.warn('Unable to save category thumbnail to IndexedDB', err);
            });
        }

        function prefetchCategories() {
            fetch('/api/categories')
                .then(res => {
                    if (!res.ok) throw new Error('Category fetch failed');
                    return res.json();
                })
                .then(cats => {
                    if (cats && cats.length) {
                        saveCachedCategories(cats);
                        prefetchCategoryImages(cats);
                        prefetchCategoryThumbnails(cats);
                    }
                })
                .catch(err => console.warn('Prefetch categories failed', err));
        }

        function prefetchCategoryImages(cats) {
            if (!Array.isArray(cats)) return;
            cats.forEach(cat => {
                if (!cat.image_url) return;
                const img = new Image();
                img.src = cat.image_url;
                img.onload = () => { cacheImage(cat.image_url); };
                img.onerror = () => { cacheImage(cat.image_url); };
            });
        }

        function prefetchCategoryThumbnails(cats) {
            if (!Array.isArray(cats)) return;
            getCachedCategoryThumbnails().then(thumbs => {
                cats.forEach(cat => {
                    if (!cat.image_url || (thumbs && thumbs[cat.name])) return;
                    const img = new Image();
                    // Removed Anonymous to prevent CORS issues
                    img.src = cat.image_url;
                    img.onload = () => createThumbnailFromImage(img, cat.name);
                });
            }).catch(() => {
                cats.forEach(cat => {
                    if (!cat.image_url) return;
                    const img = new Image();
                    img.src = cat.image_url;
                    img.onload = () => createThumbnailFromImage(img, cat.name);
                });
            });
        }

        function createThumbnailFromImage(img, name) {
            if (!img || !img.src || !name) return;
            if (img.src.startsWith('data:')) return;
            try {
                const maxWidth = 400;
                const maxHeight = 400;
                let width = img.width;
                let height = img.height;
                const scale = Math.min(1, maxWidth / width, maxHeight / height);
                if (scale < 1) {
                    width = Math.round(width * scale);
                    height = Math.round(height * scale);
                }

                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);
                const dataUrl = canvas.toDataURL('image/webp', 0.1);
                saveCachedCategoryThumbnail(name, dataUrl);
            } catch (err) {
                console.warn('Thumbnail creation failed', err);
            }
        }

        function cacheImage(url) {
            if (!('caches' in window) || !url) return;
            caches.open('alsalfa-dynamic-v1').then(cache => {
                cache.match(url).then(response => {
                    if (!response) cache.add(url).catch(() => null);
                }).catch(() => null);
            }).catch(() => null);
        }

        function showCategoryLoadingSkeleton() {
            const placeholders = Array(8).fill(0).map(() => `
                <div class="cat-card placeholder">
                    <div class="no-img">⌛</div>
                    <span>تحميل...</span>
                </div>`).join('');
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>اختر نوع السالفة</h2>
                    <div class="cat-grid">${placeholders}</div>
                    <p style="margin-top:20px; color:#ccc;">يتم تحميل الصور تدريجياً. يمكنك اختيار الفئة فوراً.</p>
                </div>`;
        }

        function showCategoryError() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>خطأ في التحميل</h2>
                    <p>تعذّر تحميل بيانات الفئات. حاول إعادة تحميل الصفحة أو التحقق من اتصال الإنترنت.</p>
                    <button class="btn-yellow" onclick="navigateTo('setup', {step: 3})">أعد المحاولة</button>
                </div>`;
        }

        async function renderCategorySelection(cats, fromCache = false, isFallback = false) {
            const thumbs = await getCachedCategoryThumbnails();
            const catsHtml = cats.map(c => {
                const thumbnail = thumbs[c.name];
                return `
                <div class="cat-card" data-cat-name="${c.name}">
                    ${c.image_url ? `
                        <div class="cat-image-wrapper">
                            <div class="image-placeholder">⌛</div>
                            <img src="${thumbnail || c.image_url}" alt="${c.name}">
                        </div>` : '<div class="no-img">؟</div>'}
                    <span>${c.name}</span>
                </div>`;
            }).join('');

            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>اختر نوع السالفة</h2>
                    <div class="cat-grid">${catsHtml}</div>
                    <input type="hidden" id="selected_cat">

                    <p style="margin-top:20px; font-weight:bold;">حد الفوز (نقاط):</p>
                    <div style="display: flex; gap: 10px; justify-content: center; margin-bottom: 20px;">
                        <div class="win-opt" onclick="selectWinLimit(this, 5)">5</div>
                        <div class="win-opt selected" onclick="selectWinLimit(this, 10)">10</div>
                        <div class="win-opt" onclick="selectWinLimit(this, 15)">15</div>
                        <div class="win-opt" onclick="selectWinLimit(this, 20)">20</div>
                    </div>
                    <input type="hidden" id="win_limit_val" value="10">

                    <button class="btn-yellow" onclick="startGameFinal(this)">ابدأ اللعب الآن</button>
                </div>`;

            document.querySelectorAll('.cat-card').forEach(card => {
                card.addEventListener('click', () => selectCat(card, card.dataset.catName));
            });

            loadCategoryImages();
            if (fromCache) {
                const notice = document.createElement('div');
                notice.style = 'margin-top:14px; color:#a9a9a9; font-size:14px;';
                notice.textContent = 'تم عرض الفئات من الكاش المحلي، ويتم تحميل الصور تدريجياً.';
                document.querySelector('.card').appendChild(notice);
            } else if (isFallback) {
                const notice = document.createElement('div');
                notice.style = 'margin-top:14px; color:#a9a0c2; font-size:14px;';
                notice.textContent = 'يتم عرض الفئات الأساسية أولاً، والصور تُحمّل في الخلفية.';
                document.querySelector('.card').appendChild(notice);
            }
        }

        function loadCategoryImages() {
            document.querySelectorAll('.cat-image-wrapper img').forEach(img => {
                const wrapper = img.closest('.cat-image-wrapper');

                if (img.complete) {
                    showImg(img, wrapper);
                } else {
                    img.onload = () => showImg(img, wrapper);
                }

                img.onerror = () => {
                    if (wrapper) {
                        const placeholder = wrapper.querySelector('.image-placeholder');
                        if (placeholder) placeholder.textContent = '؟';
                    }
                };
            });
        }

        function showImg(img, wrapper) {
            img.style.opacity = '1';
            if (wrapper) {
                const placeholder = wrapper.querySelector('.image-placeholder');
                if (placeholder) placeholder.remove();
            }
            const name = img.closest('.cat-card')?.dataset.catName;
            if (name && img.src && !img.src.startsWith('data:')) {
                // جلب الكاش بشكل غير متزامن دون تعطيل العرض
                getCachedCategoryThumbnails().then(thumbs => {
                    if (thumbs && !thumbs[name]) {
                        createThumbnailFromImage(img, name);
                    }
                }).catch(() => null);
            }
        }

        function startGameFinal(btn) {
            const cat = document.getElementById('selected_cat').value;
            if(!cat) return alert("اختر فئة أولاً!");
            if(btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="shuffling" style="font-size:20px; margin:0;">🌀</span> جاري البدء...';
            }
            winLimit = parseInt(document.getElementById('win_limit_val').value);
            start(cat);
        }

        async function start(category) {
            if(document.getElementById('global-exit-btn')) document.getElementById('global-exit-btn').style.display = 'block';
            const players = window.pNamesSave;
            if(Object.keys(totalScores).length === 0) players.forEach(p => totalScores[p] = 0);
            const res = await fetch('/api/game/start', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({players, category})});
            game = await res.json();
            game.players = players;
            game.category = category; // حفظ الفئة للجولة القادمة
            game.curr = 0;
            game.qIdx = 0;
            showRole();
        }

        function showRole() {
            if(game.curr >= game.players.length) { showPhase1(); return; }
            // صوت الكشف
            if(game.curr > 0) playSound('reveal');
            document.getElementById('main-ui').innerHTML = `
                <div class="card" style="animation: slideIn 0.4s ease-out">
                    <p>مرر الجهاز لـ</p><h2 style="color:var(--accent)">${game.players[game.curr]}</h2>
                    <div id="box" class="hidden" style="background:#0f0c29; padding:20px; border-radius:20px; margin:20px 0;">
                        <h3 class="reveal-text">${game.roles[game.curr] === 'spy' ? '🕵️ أنت برة السالفة!' : '🤫 السالفة هي: ' + game.word}</h3>
                    </div>
                    <button onclick="document.getElementById('box').classList.remove('hidden'); this.style.display='none'; document.getElementById('bnxt').style.display='block'; playSound('click')">اكشف الدور</button>
                    <button id="bnxt" style="display:none" onclick="game.curr++; showRole()">فهمت، التالي</button>
                </div>`;
        }

        function startTimer(callback, customTime = null) {
            if(timerInterval) clearInterval(timerInterval);
            let timeLeft = customTime || questionTimeout;
            const timerEl = document.getElementById('timer-display');
            if(timerEl) timerEl.innerText = timeLeft;

            timerInterval = setInterval(() => {
                timeLeft--;
                if(timerEl) timerEl.innerText = timeLeft;
                if(timeLeft <= 0) {
                    clearInterval(timerInterval);
                    callback();
                }
            }, 1000);
        }

        function showPhase1() {
            if(game.qIdx >= game.q_seq.length) { showPhase2(game.players[0]); return; }
            const q = game.q_seq[game.qIdx];
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="q-badge">مرحلة إجبارية</span>
                        <div style="background:var(--error); padding:5px 15px; border-radius:10px; font-weight:bold;">
                            ⏱️ <span id="timer-display">${questionTimeout}</span>
                        </div>
                    </div>
                    <div style="font-size:24px; margin:30px 0;"><b style="color:#a29bfe">${q.f}</b> يسأل <b style="color:#ff7675">${q.t}</b></div>
                    <button onclick="clearInterval(timerInterval); game.qIdx++; showPhase1()">السؤال التالي</button>
                    <button style="background: #ffec00; color: #1b1464; font-weight: 900; box-shadow: 0 0 20px rgba(255, 236, 0, 0.4);" onclick="clearInterval(timerInterval); startVoting()">إنهاء الجولة والتصويت</button>
                </div>`;
            startTimer(() => {
                game.qIdx++;
                showPhase1();
            });
        }

        function showPhase2(asker, last = "") {
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="q-badge" style="background:var(--primary)">مرحلة الاختيار الحر</span>
                        <div style="background:var(--error); padding:5px 15px; border-radius:10px; font-weight:bold;">
                            ⏱️ <span id="timer-display">${questionTimeout}</span>
                        </div>
                    </div>
                    <h3>دور <b style="color:var(--accent)">${asker}</b> يختار مين يسأل؟</h3>
                    <div id="plist"></div>
                    <button style="margin-top:20px; background: #ffec00; color: #1b1464; font-weight: 900; box-shadow: 0 0 20px rgba(255, 236, 0, 0.4);" onclick="clearInterval(timerInterval); startVoting()">بدء التصويت</button>
                </div>`;
            game.players.forEach(p => {
                if(p!==asker && p!==last) {
                    let btn = document.createElement('button');
                    btn.className = 'vote-item';
                    btn.innerText = `اسأل ${p}`;
                    btn.onclick = () => {
                        clearInterval(timerInterval);
                        showPhase2(p, asker);
                    };
                    document.getElementById('plist').appendChild(btn);
                }
            });
            startTimer(() => {
                // في المرحلة الحرة، إذا انتهى الوقت ننتقل للتصويت
                startVoting();
            });
        }

        function startVoting() { p_votes = {}; performVote(0); }

        function performVote(idx) {
            if(idx >= game.players.length) { showReveal(); return; }
            let list = game.players;
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <span>مرر لـ <b>${game.players[idx]}</b></span>
                        <div style="background:var(--error); padding:5px 15px; border-radius:10px; font-weight:bold;">
                            ⏱️ <span id="timer-display">${voteTimeout}</span>
                        </div>
                    </div>
                    <p>صوت سراً: منو اللي برة السالفة؟</p>
                    <div id="vbox"></div>
                </div>`;
            list.forEach(p => {
                let btn = document.createElement('button'); btn.className = 'vote-item'; btn.innerText = p;
                btn.onclick = () => {
                    clearInterval(timerInterval);
                    p_votes[game.players[idx]] = p;
                    performVote(idx+1);
                };
                document.getElementById('vbox').appendChild(btn);
            });

            startTimer(() => {
                // اختيار لاعب عشوائي (غير الشخص نفسه) عند انتهاء الوقت
                const me = game.players[idx];
                const others = game.players.filter(p => p !== me);
                const randomChoice = others[Math.floor(Math.random() * others.length)];
                p_votes[me] = randomChoice;
                performVote(idx+1);
            }, voteTimeout);
        }

        function showReveal() {
            document.getElementById('main-ui').innerHTML = `<div class="card"><h1>جاري فرز الأصوات...</h1><div class="shuffling">🌀</div></div>`;
            setTimeout(() => {
                const spy = game.players[game.spy_idx];
                let resultsHtml = "";
                let voteCounts = {};
                game.players.forEach(p => voteCounts[p] = 0);

                Object.keys(p_votes).forEach(voter => {
                    const target = p_votes[voter];
                    voteCounts[target]++;
                    const isCorrect = (target === spy);
                    resultsHtml += `<div style="margin:5px 0;">${voter} صوّت لـ ${target} ${isCorrect?'✅':'❌'}</div>`;
                });

                // هل انكشف الجاسوس؟ (الأغلبية صوتت عليه)
                let maxVotes = 0, votedOut = "";
                for(let p in voteCounts) { if(voteCounts[p] > maxVotes) { maxVotes = voteCounts[p]; votedOut = p; } }
                game.spyCaught = (votedOut === spy);

                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h1>اللي برة السالفة هو:</h1>
                        <h2 style="color:var(--error); font-size:40px;">${spy}</h2>
                        <div style="background:#0f0c29; padding:15px; border-radius:15px; margin:20px 0; text-align:right;">${resultsHtml}</div>
                        <h3>${game.spyCaught ? '🚨 تم كشف الجاسوس!' : '🏃 هرب الجاسوس!'}</h3>
                        <button onclick="spyGuess()">التالي</button>
                    </div>`;
            }, 2000);
        }

        function spyGuess() {
            let h = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h3>خمن وش السالفة؟</h3>
                    <div style="background:var(--error); padding:5px 15px; border-radius:10px; font-weight:bold;">
                        ⏱️ <span id="timer-display">${spyGuessTimeout}</span>
                    </div>
                </div>
                <div id="guess_grid">`;
            game.guesses.forEach(g => h += `<div class="vote-item guess-item" onclick="clearInterval(timerInterval); handleSpyGuess(this, '${g.replace(/'/g, "\\\\'")}')">${g}</div>`);
            h += `</div>`;
            document.getElementById('main-ui').innerHTML = `<div class="card">${h}</div>`;

            startTimer(() => {
                const randomGuess = game.guesses[Math.floor(Math.random() * game.guesses.length)];
                handleSpyGuess(null, randomGuess);
            }, spyGuessTimeout);
        }

        function handleSpyGuess(el, guessedWord) {
            const correctWord = game.word;
            const items = document.querySelectorAll('.guess-item');

            items.forEach(item => {
                item.style.pointerEvents = "none";
                if (item.innerText === correctWord) {
                    item.style.background = "var(--success)";
                    item.style.boxShadow = "0 0 20px var(--success)";
                }
            });

            if (guessedWord === correctWord) {
                playSound('win'); // صوت النجاح
            } else {
                el.style.background = "var(--error)";
                el.style.boxShadow = "0 0 20px var(--error)";
                playSound('fail'); // صوت الفشل
            }

            setTimeout(() => {
                finish(guessedWord);
            }, 3000);
        }

        function finish(guessedWord) {
            const spy = game.players[game.spy_idx];
            const spyGuessedRight = (guessedWord === game.word);
            let roundMsg = "";

            // توزيع النقاط حسب القواعد الصحيحة:
            // 1. اللاعبين (غير الجاسوس) اللي صوّتوا صح على الجاسوس ياخذون نقطة
            game.players.forEach(p => {
                if(p !== spy && p_votes[p] === spy) {
                    totalScores[p] = (totalScores[p] || 0) + 1;
                }
            });

            // 2. الجاسوس ياخذ نقطة فقط إذا عرف الكلمة (الشغلة)
            if (spyGuessedRight) {
                totalScores[spy] = (totalScores[spy] || 0) + 1;
                roundMsg = "الجاسوس عرف السالفة وأخذ نقطة!";
            } else {
                roundMsg = "الجاسوس ما عرف السالفة.";
            }

            if (game.spyCaught) {
                roundMsg += " وتم كشفه من اللاعبين (نقاط لمن صوّت صح)!";
            } else {
                roundMsg += " وهرب من التصويت!";
            }

            // فحص الفائز النهائي
            let sortedScores = Object.entries(totalScores).sort((a,b) => b[1]-a[1]);
            let hasWinner = sortedScores.some(s => s[1] >= winLimit);

            if(hasWinner) {
                playSound('win');
                // ابلاغ السيرفر بالفائز لتحديث الاحصائيات المحلية
                const winnerName = sortedScores[0][0];
                fetch('/api/game/report_winner', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({player_name: winnerName, user_id: currentUser.user_id})
                }).catch(e => console.error("Report winner failed", e));

                let podiumHtml = "";
                const medals = ["🥇 المركز الأول", "🥈 المركز الثاني", "🥉 المركز الثالث"];
                const colors = ["gold", "silver", "#cd7f32"];

                for(let i=0; i<3; i++) {
                    if(sortedScores[i]) {
                        podiumHtml += `<div style="color:${colors[i]}; font-size:${24-i*2}px; margin:10px 0; font-weight:bold;">
                            ${medals[i]}: ${sortedScores[i][0]} (${sortedScores[i][1]} نقطة)
                        </div>`;
                    }
                }

                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h1 style="color:var(--accent)">🏆 النتائج النهائية 🏆</h1>
                        <div style="margin: 30px 0; background: rgba(0,0,0,0.3); padding: 20px; border-radius: 20px;">
                            ${podiumHtml}
                        </div>
                        <button onclick="showMenu()">العودة للقائمة الرئيسية</button>
                    </div>`;
            } else {
                let scoresList = "";
                sortedScores.forEach(([p, s]) => {
                    scoresList += `<div class="score-item"><span>${p}</span> <b>${s}</b></div>`;
                });
                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2 style="color:${spyGuessedRight? 'var(--success)':'var(--error)'}">${spyGuessedRight?'صح!':'خطأ!'} السالفة كانت: ${game.word}</h2>
                        <p>${roundMsg}</p>
                        <hr style="border:1px solid #3c339e; margin:15px 0;">
                        <h3>لوحة الصدارة (الهدف: ${winLimit}):</h3>
                        <div style="margin-bottom:20px;">${scoresList}</div>
                        <button onclick="start(game.category)">بدء جولة جديدة</button>
                        <button style="background:#636e72" onclick="showMenu()">إنهاء الجلسة</button>
                    </div>`;
            }
        }

        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('open');
            updateSidebar();
            updateInstallButtonVisibility();
        }
        function showLoading(message = "جارٍ التحميل...") {
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>${message}</h2>
                    <div style="margin: 20px 0; text-align:center;">
                        <div class="loading-spinner"></div>
                    </div>
                </div>`;
        }
        function updateSidebar() { if(currentUser) {
            document.getElementById('user-display').innerText = currentUser.player_name;
            if(currentUser.username_key === 'admin') {
                if(!document.getElementById('admin-btn')) {
                    let btn = document.createElement('button');
                    btn.id = 'admin-btn';
                    btn.innerText = "🛠️ لوحة الإدارة";
                    btn.style.background = "var(--accent)";
                    btn.style.color = "black";
                    btn.onclick = () => navigateTo('admin');
                    document.getElementById('sidebar').appendChild(btn);
                }
            }
        }}

        async function showAdminDashboard(push = true) {
            if(push) {
                history.pushState({screen: 'admin'}, "");
                toggleSidebar();
            }
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>لوحة التحكم الإدارية</h2>
                    <button onclick="adminManagePlayers()">👥 إدارة اللاعبين</button>
                    <button onclick="adminManageCategories()">📂 إدارة الفئات والكلمات</button>
                    <button onclick="adminManageTimeouts()">⏱️ إعدادات المهل الزمنية</button>
                    <button style="background:#636e72" onclick="navigateTo('menu')">رجوع</button>
                </div>`;
        }

        function adminManageTimeouts() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>⏱️ إعدادات المهل والأصوات</h2>
                    <div style="background:rgba(0,0,0,0.2); padding:15px; border-radius:15px; margin:20px 0; text-align:right; max-height:450px; overflow-y:auto;">
                        <h3 style="color:var(--accent); border-bottom:1px solid #3c339e; padding-bottom:5px;">المهل الزمنية (بالثواني)</h3>
                        <label>وقت مهلة السؤال:</label>
                        <div style="display:flex; gap:10px; margin-bottom:15px;">
                            <input type="number" id="timeout_setting" value="${questionTimeout}">
                            <button onclick="saveAdminSetting('question_timeout', 'timeout_setting')" style="width:80px; background:var(--success)">حفظ</button>
                        </div>
                        <label>وقت مهلة التصويت:</label>
                        <div style="display:flex; gap:10px; margin-bottom:15px;">
                            <input type="number" id="vote_timeout_setting" value="${voteTimeout}">
                            <button onclick="saveAdminSetting('vote_timeout', 'vote_timeout_setting')" style="width:80px; background:var(--success)">حفظ</button>
                        </div>

                        <h3 style="color:var(--accent); border-bottom:1px solid #3c339e; padding-bottom:5px; margin-top:20px;">روابط الأصوات (URL)</h3>
                        <label>صوت النقر/التالي:</label>
                        <div style="display:flex; flex-direction:column; gap:5px; margin-bottom:15px;">
                            <input type="text" id="sound_click_setting" value="${soundClickUrl}" dir="ltr">
                            <button onclick="saveAdminSetting('sound_click', 'sound_click_setting')" style="background:var(--success); padding:8px;">حفظ الرابط</button>
                        </div>
                        <label>صوت كشف الدور:</label>
                        <div style="display:flex; flex-direction:column; gap:5px; margin-bottom:15px;">
                            <input type="text" id="sound_reveal_setting" value="${soundRevealUrl}" dir="ltr">
                            <button onclick="saveAdminSetting('sound_reveal', 'sound_reveal_setting')" style="background:var(--success); padding:8px;">حفظ الرابط</button>
                        </div>
                        <label>صوت الفوز:</label>
                        <div style="display:flex; flex-direction:column; gap:5px; margin-bottom:15px;">
                            <input type="text" id="sound_win_setting" value="${soundWinUrl}" dir="ltr">
                            <button onclick="saveAdminSetting('sound_win', 'sound_win_setting')" style="background:var(--success); padding:8px;">حفظ الرابط</button>
                        </div>
                        <label>صوت الخطأ/الفشل:</label>
                        <div style="display:flex; flex-direction:column; gap:5px; margin-bottom:15px;">
                            <input type="text" id="sound_fail_setting" value="${soundFailUrl}" dir="ltr">
                            <button onclick="saveAdminSetting('sound_fail', 'sound_fail_setting')" style="background:var(--success); padding:8px;">حفظ الرابط</button>
                        </div>
                    </div>
                    <button style="background:#636e72" onclick="showAdminDashboard(false)">رجوع</button>
                </div>`;
        }

        async function saveAdminSetting(key, inputId) {
            const val = document.getElementById(inputId).value;
            const res = await fetch('/api/admin/settings/update', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({key: key, value: val})
            });
            const d = await res.json();
            if(d.success) {
                // تحديث القيم محلياً فوراً
                if(key === 'question_timeout') questionTimeout = parseInt(val);
                if(key === 'vote_timeout') voteTimeout = parseInt(val);
                if(key === 'spy_guess_timeout') spyGuessTimeout = parseInt(val);
                if(key === 'sound_click') { soundClickUrl = val; sounds.click = new Audio(val); }
                if(key === 'sound_reveal') { soundRevealUrl = val; sounds.reveal = new Audio(val); }
                if(key === 'sound_win') { soundWinUrl = val; sounds.win = new Audio(val); }
                if(key === 'sound_fail') { soundFailUrl = val; sounds.fail = new Audio(val); }
                alert("تم التحديث بنجاح ✅");
            }
        }

        async function adminManagePlayers() {
            showLoading();
            const res = await fetch('/api/admin/players');
            const players = await res.json();
            let h = `<h2>قائمة اللاعبين</h2><div style="max-height:400px; overflow-y:auto;">`;            players.forEach(p => {
                h += `<div class="score-item">
                    <div style="text-align:right">
                        <b>${p.player_name}</b> (@${p.username_key})<br>
                        <small>الفوز الإجمالي: ${p.total_wins || 0}</small>
                    </div>
                </div>`;
            });
            h += `</div><button onclick="showAdminDashboard()">رجوع</button>`;
            document.getElementById('main-ui').innerHTML = `<div class="card">${h}</div>`;
        }

        async function adminManageCategories() {
            try {
                showLoading();
                const res = await fetch('/api/categories');
                const cats = await res.json();
                let h = `<h2>الفئات (الأنواع)</h2>
                    <button style="background:var(--success); margin-bottom:15px;" onclick="showAddCategoryForm()">➕ إضافة فئة جديدة</button>
                    <div id="cat-form-container"></div>
                    <div style="max-height:400px; overflow-y:auto; text-align:right;">`;
                cats.forEach(c => {
                    const catJson = JSON.stringify(c).replace(/"/g, '&quot;');
                    const catNameJson = JSON.stringify(c.name);
                    h += `<div class="score-item" style="flex-direction:column; align-items:flex-start;">
                        <div style="display:flex; justify-content:space-between; width:100%; align-items:center;">
                            <div style="display:flex; align-items:center;">
                                ${c.image_url ? `<img src="${c.image_url}" style="width:40px; height:40px; border-radius:10px; margin-left:10px; object-fit:cover;">` : ''}
                                <div>
                                    <b style="font-size:18px;">${c.name}</b>
                                    <div style="font-size:12px; color:var(--accent)">الترتيب: ${c.display_order}</div>
                                </div>
                            </div>
                            <div style="display:flex; gap:5px;">
                                <button style="width:auto; padding:5px 10px; margin:0; background:var(--success)" onclick="manageWords(${catNameJson})">الكلمات</button>
                                <button style="width:auto; padding:5px 10px; margin:0; background:var(--primary)" onclick="editCategory(${catJson})">تعديل</button>
                                <button style="width:auto; padding:5px 10px; margin:0; background:var(--error)" onclick="deleteCategory(${c.id})">حذف</button>
                            </div>
                        </div>
                    </div>`;
                });
                h += `</div><button onclick="showAdminDashboard()">رجوع</button>`;
                document.getElementById('main-ui').innerHTML = `<div class="card">${h}</div>`;
            } catch (err) {
                console.error('Failed to load admin categories:', err);
                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2>حدث خطأ أثناء تحميل الفئات</h2>
                        <p>${err.message || err}</p>
                        <button onclick="showAdminDashboard()">رجوع</button>
                    </div>`;
            }
        }

        function showAddCategoryForm() {
            const container = document.getElementById('cat-form-container');
            container.innerHTML = `
                <div id="cat-form" style="background:rgba(0,0,0,0.2); padding:15px; border-radius:15px; margin-bottom:20px; border: 1px solid var(--success); animation: fadeIn 0.3s;">
                    <h3 id="form-title">إضافة فئة جديدة</h3>
                    <input id="cat_id" type="hidden">
                    <input id="cat_name" placeholder="اسم الفئة">
                    <div style="text-align:right; margin:10px 0;">
                        <label>صورة الفئة:</label>
                        <input type="file" id="cat_file" accept="image/*" style="padding:10px; background:#0f0c29;">
                    </div>
                    <input id="cat_order" type="number" placeholder="التسلسل (0, 1, 2...)" value="0">
                    <div style="display:flex; gap:10px;">
                        <button id="cat-save-btn" onclick="saveCategory()">حفظ الفئة</button>
                        <button style="background:#636e72;" onclick="resetCatForm()">إغلاق</button>
                    </div>
                </div>`;
            document.getElementById('cat-form').scrollIntoView({behavior: 'smooth'});
        }

        function editCategory(c) {
            showAddCategoryForm();
            document.getElementById('form-title').innerText = "تعديل الفئة: " + c.name;
            document.getElementById('cat_id').value = c.id;
            document.getElementById('cat_name').value = c.name;
            document.getElementById('cat_order').value = c.display_order;
            window.oldCatName = c.name;
            window.editingImage = c.image_url;
            document.getElementById('cat-save-btn').innerText = "تحديث الفئة";
        }

        function resetCatForm() {
            document.getElementById('cat-form-container').innerHTML = "";
            window.oldCatName = null;
            window.editingImage = null;
        }

        async function compressImageFile(file, quality = 0.05, maxWidth = 800, maxHeight = 800) {
            return new Promise((resolve, reject) => {
                const url = URL.createObjectURL(file);
                const img = new Image();
                img.onload = async () => {
                    let width = img.width;
                    let height = img.height;
                    const scale = Math.min(1, maxWidth / width, maxHeight / height);
                    if (scale < 1) {
                        width = Math.round(width * scale);
                        height = Math.round(height * scale);
                    }

                    const canvas = document.createElement('canvas');
                    canvas.width = width;
                    canvas.height = height;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, width, height);

                    const supportedType = canvas.toDataURL('image/webp', quality).startsWith('data:image/webp') ? 'image/webp' : 'image/jpeg';
                    const result = canvas.toDataURL(supportedType, quality);
                    URL.revokeObjectURL(url);
                    resolve(result);
                };
                img.onerror = (err) => {
                    URL.revokeObjectURL(url);
                    reject(err);
                };
                img.src = url;
            });
        }

        async function saveCategory() {
            const id = document.getElementById('cat_id').value;
            const name = document.getElementById('cat_name').value;
            const order = document.getElementById('cat_order').value;
            const fileInput = document.getElementById('cat_file');

            if(!name) return alert("الرجاء إدخال اسم الفئة");

            let imageUrl = window.editingImage || null;
            if (fileInput.files.length > 0) {
                try {
                    imageUrl = await compressImageFile(fileInput.files[0], 0.05, 800, 800);
                } catch (err) {
                    console.warn('Image compression failed', err);
                    imageUrl = await new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onload = (e) => resolve(e.target.result);
                        reader.readAsDataURL(fileInput.files[0]);
                    });
                }
            }

            const endpoint = id ? '/api/admin/category/update' : '/api/admin/category/add';
            const payload = { id, name, display_order: parseInt(order), image_url: imageUrl };
            if (id && window.oldCatName) payload.old_name = window.oldCatName;

            const res = await fetch(endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            if ((await res.json()).success) {
                resetCatForm();
                adminManageCategories();
            }
        }

        async function deleteCategory(id) {
            if(!confirm("هل أنت متأكد من حذف هذه الفئة وكل كلماتها؟")) return;
            await fetch('/api/admin/category/delete', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({id})});
            adminManageCategories();
        }

        async function manageWords(catName) {
            try {
                showLoading();
                const res = await fetch('/api/admin/words');
                const allWords = await res.json();
            // استخدام trim للمقارنة لضمان عدم وجود مساحات مخفية
            const cleanCatName = catName.trim();
            const words = allWords.filter(w => (w.category || "").trim() === cleanCatName);

            let h = `<h2>كلمات قسم: ${catName}</h2>
                <div id="word-form-container" style="background:rgba(0,0,0,0.2); padding:15px; border-radius:15px; margin-bottom:20px;">
                    <input id="word_id" type="hidden">
                    <input id="new_word_val" placeholder="الكلمة">
                    <div style="display:flex; gap:10px; margin-top:10px;">
                        <button id="word-save-btn" onclick="addWordToCat(${JSON.stringify(catName)})">إضافة للقسم</button>
                        <button id="word-cancel-btn" style="background:#636e72; display:none;" onclick="resetWordForm(${JSON.stringify(catName)})">إلغاء</button>
                    </div>
                </div>
                <div style="max-height:400px; overflow-y:auto; text-align:right;">`;

            if (words.length === 0) {
                h += `<p id="no-words-msg" style="text-align:center; color:#888; padding:20px;">لا توجد كلمات في هذا القسم حالياً.</p>`;
            }

            words.forEach(w => {
                h += `<div class="score-item" id="word-item-${w.id}">
                    <span style="font-size:18px;">${w.word}</span>
                    <div style="display:flex; gap:5px;">
                        <button style="width:auto; padding:5px 10px; margin:0; background:var(--primary)" onclick="editWord(${w.id}, ${JSON.stringify(w.word)}, ${JSON.stringify(catName)})">تعديل</button>
                        <button style="width:auto; padding:5px 10px; margin:0; background:var(--error)" onclick="deleteWord(${w.id}, ${JSON.stringify(catName)})">حذف</button>
                    </div>
                </div>`;
            });
            h += `</div><button onclick="adminManageCategories()">رجوع للفئات</button>`;
            document.getElementById('main-ui').innerHTML = `<div class="card">${h}</div>`;
            } catch (err) {
                console.error('Failed to load words for category:', err);
                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2>حدث خطأ أثناء تحميل الكلمات</h2>
                        <p>${err.message || err}</p>
                        <button onclick="adminManageCategories()">رجوع للفئات</button>
                    </div>`;
            }
        }

        function editWord(id, word, catName) {
            document.getElementById('word_id').value = id;
            document.getElementById('new_word_val').value = word;
            document.getElementById('word-save-btn').innerText = "تحديث الكلمة";
            document.getElementById('word-save-btn').onclick = () => updateWordInCat(catName);
            document.getElementById('word-cancel-btn').style.display = "block";
            document.getElementById('new_word_val').focus();
        }

        function resetWordForm(catName) {
            document.getElementById('word_id').value = "";
            document.getElementById('new_word_val').value = "";
            document.getElementById('word-save-btn').innerText = "إضافة للقسم";
            document.getElementById('word-save-btn').onclick = () => addWordToCat(catName);
            document.getElementById('word-cancel-btn').style.display = "none";
        }

        async function updateWordInCat(catName) {
            const id = document.getElementById('word_id').value;
            const word = document.getElementById('new_word_val').value.trim();
            if(!word) return;
            const res = await fetch('/api/admin/word/update', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id, word})
            });
            const d = await res.json();
            if(d.success) manageWords(catName);
        }

        async function addWordToCat(cat) {
            const word = document.getElementById('new_word_val').value.trim();
            if(!word) return;
            const res = await fetch('/api/admin/add_word', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({category: cat, word})
            });
            const d = await res.json();
            if(d.success) manageWords(cat);
        }

        async function deleteWord(id, cat) {
            await fetch('/api/admin/word/delete', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({id})});
            manageWords(cat);
        }

        function showReports(push = true) {
            if(push) {
                history.pushState({screen: 'reports'}, "");
                toggleSidebar();
            }
            renderReportsUI();
        }

        async function renderReportsUI() {
            // تحديث بيانات المستخدم للحصول على أحدث النقاط للاعبين المحليين
            const resAuth = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: currentUser.username_key, password: currentUser.password_key})
            });
            const dAuth = await resAuth.json();
            if(dAuth.success) {
                currentUser = dAuth.user;
                localStorage.setItem('user', JSON.stringify(currentUser));
            }

            let players = (currentUser.saved_players || []).map(p => typeof p === 'string' ? {name: p, wins: 0} : p);
            players.sort((a, b) => (b.wins || 0) - (a.wins || 0));

            let h = `
                <div style="display:flex; gap:5px; margin-bottom:15px;">
                    <button style="flex:1; margin:0; background:var(--primary); font-size:14px;" disabled>📊 محلي</button>
                    <button style="flex:1; margin:0; background:rgba(255,255,255,0.1); font-size:14px;" onclick="navigateTo('global_rankings')">🌍 عالمي (أونلاين)</button>
                </div>
                <h2>📊 تقارير لاعبيك المحليين</h2>
                <p style="font-size:14px; color:#aaa;">ترتيب اللاعبين الذين أضفتهم حسب عدد مرات الفوز</p>
                <div style="max-height:400px; overflow-y:auto; margin:15px 0;">`;

            players.forEach((p, i) => {
                let medal = "";
                if(i === 0 && p.wins > 0) medal = "👑 ";
                h += `<div class="score-item" style="border-left: 4px solid ${i<3 ? 'var(--accent)' : '#333'}">
                    <div style="text-align:right">
                        <b>${medal}${p.name}</b>
                    </div>
                    <div style="text-align:left">
                        <b style="color:var(--success)">${p.wins || 0}</b> <small>فوز</small>
                    </div>
                </div>`;
            });

            if(players.length === 0) h += `<p style="padding:20px;">لم تقم بإضافة أي لاعبين محليين بعد.</p>`;

            if(players.length > 0) {
                const least = players[players.length - 1];
                h += `<div style="margin-top:20px; padding:10px; background:rgba(235, 77, 75, 0.1); border-radius:15px; font-size:14px;">
                    🐢 الأقل فوزاً حالياً: <b>${least.name}</b>
                </div>`;
            }

            h += `</div><button onclick="navigateTo('menu')">رجوع</button>`;
            document.getElementById('main-ui').innerHTML = `<div class="card">${h}</div>`;
        }

        async function showGlobalRankings(push = true) {
            if(push) {
                history.pushState({screen: 'global_rankings'}, "");
                if(document.getElementById('sidebar').classList.contains('open')) toggleSidebar();
            }
            showLoading("جاري تحميل الترتيب العالمي...");
            try {
                const res = await fetch('/api/online/rankings');
                const rankings = await res.json();

                let h = `
                    <div style="display:flex; gap:5px; margin-bottom:15px;">
                        <button style="flex:1; margin:0; background:rgba(255,255,255,0.1); font-size:14px;" onclick="navigateTo('reports')">📊 محلي</button>
                        <button style="flex:1; margin:0; background:var(--primary); font-size:14px;" disabled>🌍 عالمي (أونلاين)</button>
                    </div>
                    <h2>🌍 المتصدرين عالمياً</h2>
                    <p style="font-size:14px; color:#aaa;">أفضل 50 لاعباً في وضع الأونلاين</p>
                    <div style="max-height:400px; overflow-y:auto; margin:15px 0;">`;

                if(rankings.length === 0) {
                    h += `<p style="padding:40px;">لا يوجد لاعبين في الترتيب حالياً.</p>`;
                } else {
                    rankings.forEach((p, i) => {
                        let medal = "";
                        if(i === 0) medal = "🥇 ";
                        else if(i === 1) medal = "🥈 ";
                        else if(i === 2) medal = "🥉 ";

                        h += `<div class="score-item" style="border-left: 4px solid ${i<3 ? 'var(--accent)' : '#333'}">
                            <div style="text-align:right">
                                <b>${medal}${p.player_name}</b>
                            </div>
                            <div style="text-align:left">
                                <b style="color:var(--accent)">${p.online_points}</b> <small>نقطة</small>
                            </div>
                        </div>`;
                    });
                }

                h += `</div><button onclick="navigateTo('menu')">رجوع</button>`;
                document.getElementById('main-ui').innerHTML = `<div class="card">${h}</div>`;
            } catch(e) {
                document.getElementById('main-ui').innerHTML = `<div class="card"><h2>فشل تحميل البيانات</h2><button onclick="navigateTo('menu')">رجوع</button></div>`;
            }
        }
        function confirmExitGame() {
            if(confirm("هل أنت متأكد أنك تريد إلغاء اللعبة والعودة للقائمة الرئيسية؟")) {
                if(timerInterval) clearInterval(timerInterval);
                if(currentRoom) {
                    leaveRoom();
                } else {
                    totalScores = {};
                    showMenu();
                }
            }
        }

        function logout() { localStorage.clear(); location.href = "/"; }

        const sounds = {
            click: null,
            reveal: null,
            win: null,
            fail: null
        };
        function playSound(name) {
            if(sounds[name]) {
                sounds[name].currentTime = 0;
                sounds[name].play().catch(()=>null);
            }
        }

        // PWA Registration and Install Prompt
        let deferredPrompt;
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/sw.js')
                    .then(reg => console.log('SW Registered', reg))
                    .catch(err => console.log('SW Failed', err));
            });
        }

        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            showInstallBanner();
            updateInstallButtonVisibility();
        });

        function updateInstallButtonVisibility() {
            // الزر الآن يظهر دائماً ليعطي خيارات يدوية خاصة للآيفون
            const btn = document.getElementById('install-btn-sidebar');
            const modalBtn = document.getElementById('modal-install-btn');

            if (modalBtn) {
                if (!deferredPrompt) {
                    modalBtn.style.opacity = "0.5";
                    modalBtn.innerText = "✨ التثبيت التلقائي غير مدعوم";
                } else {
                    modalBtn.style.opacity = "1";
                    modalBtn.innerText = "✨ تثبيت التطبيق (PWA)";
                }
            }
        }

        function showInstallOptions() {
            document.getElementById('installModal').style.display = 'block';
            if(document.getElementById('sidebar').classList.contains('open')) toggleSidebar();
        }

        function closeInstallModal() {
            document.getElementById('installModal').style.display = 'none';
        }

        function showShortcutGuide() {
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
            if (isIOS) {
                alert("للإضافة في آيفون:\\n1. اضغط على زر 'مشاركة' (Share) في المتصفح بالأسفل.\\n2. اختر 'إضافة إلى الشاشة الرئيسية' (Add to Home Screen).");
            } else {
                alert("للإضافة كاختصار:\\n1. اضغط على نقاط القائمة الثلاث في المتصفح بالأعلى.\\n2. اختر 'إضافة إلى الشاشة الرئيسية' أو 'تثبيت التطبيق'.");
            }
            closeInstallModal();
        }

        async function installApp() {
            if (!deferredPrompt) {
                showShortcutGuide();
                return;
            }
            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;
            if (outcome === 'accepted') {
                console.log('User accepted install');
            }
            deferredPrompt = null;
            updateInstallButtonVisibility();
            const banner = document.getElementById('install-banner');
            if (banner) banner.remove();
            closeInstallModal();
        }

        function showInstallBanner() {
            if (document.getElementById('install-banner')) return;
            const banner = document.createElement('div');
            banner.id = 'install-banner';
            banner.style = "position:fixed; bottom:20px; left:20px; right:20px; background:var(--primary); padding:15px; border-radius:15px; display:flex; justify-content:space-between; align-items:center; z-index:2000; box-shadow: 0 5px 15px rgba(0,0,0,0.5);";
            banner.innerHTML = `
                <span style="font-weight:bold;">ثبت التطبيق لتجربة أفضل! 📱</span>
                <div style="display:flex; gap:10px;">
                    <button onclick="installApp()" style="width:auto; padding:5px 15px; margin:0; background:var(--accent); color:black;">تثبيت</button>
                    <button onclick="this.parentElement.parentElement.remove()" style="width:auto; padding:5px 10px; margin:0; background:rgba(0,0,0,0.2);">إغلاق</button>
                </div>
            `;
            document.body.appendChild(banner);
        }

        init();
    </script>
</body>
</html>
"""
