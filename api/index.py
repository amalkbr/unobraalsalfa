from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import json
import random
import string
import os
import time
import psycopg2
from .database import get_db_conn, RealDictCursor
from .domino import router as domino_router
from .xo import router as xo_router
from .uno import router as uno_router

app = FastAPI()
app.include_router(domino_router)
app.include_router(xo_router)
app.include_router(uno_router)

# --- Database Connection ---
DB_INITIALIZED = False

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
                    game_type TEXT DEFAULT 'spy',
                    max_players INTEGER DEFAULT 10,
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
                    team TEXT,
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
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_room_players_code_user ON room_players(room_code, user_id)",
                "CREATE TABLE IF NOT EXISTS announcements (id SERIAL PRIMARY KEY, text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
                "CREATE TABLE IF NOT EXISTS feedback (id SERIAL PRIMARY KEY, announcement_id INTEGER REFERENCES announcements(id) ON DELETE CASCADE, user_id BIGINT, player_name TEXT, text TEXT, type TEXT, original_text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS game_type TEXT DEFAULT 'spy'",
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS max_players INTEGER DEFAULT 10",
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS room_code TEXT",
                "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS host_id BIGINT",
                "ALTER TABLE room_players ADD COLUMN IF NOT EXISTS team TEXT",
                "ALTER TABLE room_players ADD COLUMN IF NOT EXISTS room_code TEXT",
                "ALTER TABLE room_players ADD COLUMN IF NOT EXISTS said_uno BOOLEAN DEFAULT FALSE"
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
async def home():
    response = HTMLResponse(content=HTML_TEMPLATE)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/manifest.json")
async def manifest():
    # إضافة طابع زمني (Timestamp) لإجبار المتصفح على تحديث الأيقونة
    import time
    version = int(time.time())
    icon_url = f"/api/app_icon.png?v={version}"

    manifest_data = {
        "name": "أونو وبرا السالفة",
        "short_name": "السالفة",
        "description": "لعبة برا السالفة الجماعية - استمتع مع أصدقائك في المجلس أو أونلاين!",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f0c29",
        "theme_color": "#6c5ce7",
        "orientation": "portrait",
        "icons": [
            { "src": icon_url, "sizes": "192x192", "type": "image/png" },
            { "src": icon_url, "sizes": "512x512", "type": "image/png" }
        ],
        "screenshots": [
            { "src": icon_url, "sizes": "512x512", "type": "image/png", "form_factor": "wide", "label": "Home Screen" },
            { "src": icon_url, "sizes": "512x512", "type": "image/png", "form_factor": "narrow", "label": "Home Screen" }
        ]
    }
    response = JSONResponse(content=manifest_data)
    # منع التخزين المؤقت لملف المانيفست
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

import base64
from fastapi import Response
from fastapi.responses import RedirectResponse

@app.get("/api/app_icon.png")
async def get_app_icon():
    conn = get_db_conn()
    default_icon = "https://cdn-icons-png.flaticon.com/512/8030/8030198.png"
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM settings WHERE key = 'app_icon_data'")
                row = cur.fetchone()
                if row and row[0]:
                    try:
                        img_data = base64.b64decode(row[0])
                        return Response(content=img_data, media_type="image/png")
                    except: pass
        finally:
            conn.close()
    return RedirectResponse(url=default_icon)

@app.post("/api/admin/upload_icon")
async def upload_icon(request: Request):
    form = await request.form()
    file = form.get("icon")
    if not file: return {"success": False, "msg": "لم يتم اختيار ملف"}

    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024: # رفع الحد لـ 2 ميجا لضمان المرونة
        return {"success": False, "msg": "حجم الصورة كبير جداً، يرجى اختيار صورة أصغر"}

    encoded = base64.b64encode(contents).decode('utf-8')
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "فشل الاتصال بقاعدة البيانات"}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO settings (key, value) VALUES ('app_icon_data', %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (encoded,))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "msg": str(e)}
    finally:
        conn.close()

@app.get("/api/announcements")
async def get_announcements():
    conn = get_db_conn()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM announcements ORDER BY created_at DESC LIMIT 20")
            announcements = cur.fetchall()

            # Fetch feedback for each
            for ann in announcements:
                cur.execute("SELECT * FROM feedback WHERE announcement_id = %s ORDER BY created_at ASC", (ann['id'],))
                ann['feedback'] = cur.fetchall()
            return announcements
    except: return []
    finally: conn.close()

@app.post("/api/feedback/add")
async def add_feedback(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO feedback (announcement_id, user_id, player_name, text, type)
                VALUES (%s, %s, %s, %s, %s)
            """, (data['announcement_id'], data['user_id'], data['player_name'], data['text'], data['type']))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@app.post("/api/feedback/update")
async def update_feedback(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if it's a suggestion to keep original text
            cur.execute("SELECT type, text, original_text FROM feedback WHERE id = %s", (data['id'],))
            row = cur.fetchone()
            if not row: return {"success": False}

            if row['type'] == 'suggestion' and not row['original_text']:
                # Save first text as original
                cur.execute("UPDATE feedback SET text = %s, original_text = %s WHERE id = %s", (data['text'], row['text'], data['id']))
            else:
                cur.execute("UPDATE feedback SET text = %s WHERE id = %s", (data['text'], data['id']))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@app.post("/api/feedback/delete")
async def delete_feedback(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM feedback WHERE id = %s", (data['id'],))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@app.post("/api/admin/announcements/add")
async def add_announcement(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO announcements (text) VALUES (%s)", (data['text'],))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@app.post("/api/admin/announcements/update")
async def update_announcement(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE announcements SET text = %s WHERE id = %s", (data['text'], data['id']))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@app.post("/api/admin/announcements/delete")
async def delete_announcement(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM announcements WHERE id = %s", (data['id'],))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "msg": str(e)}
    finally: conn.close()

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
        "sound_fail": "",
        "app_icon_url": "https://cdn-icons-png.flaticon.com/512/8030/8030198.png"
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
            # استخدام ON CONFLICT لضمان إنشاء الإعداد إذا لم يكن موجوداً
            cur.execute("""
                INSERT INTO settings (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (data['key'], str(data['value'])))
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

@app.post("/api/domino/create")
async def create_domino_room_endpoint(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        user_id = int(data['user_id'])
        player_name = data['player_name']
        max_players = int(data.get('max_players', 4))
        room_code = ''.join(random.choices(string.ascii_uppercase, k=4))

        with conn.cursor() as cur:
            # 1. تحديد نوع عمود الفريق (نصي أم رقمي) لتجنب الأخطاء
            cur.execute("SELECT data_type FROM information_schema.columns WHERE table_name = 'room_players' AND column_name = 'team'")
            team_col = cur.fetchone()
            team_val = 'A'
            if team_col and 'int' in team_col[0].lower():
                team_val = 0

            # 2. إدخال الغرفة
            cur.execute("""
                INSERT INTO rooms (room_code, room_id, host_id, creator_id, status, game_type, win_limit, max_players)
                VALUES (%s, %s, %s, %s, 'lobby', 'domino', 101, %s)
                ON CONFLICT (room_code) DO NOTHING
            """, (room_code, room_code, user_id, user_id, max_players))

            # 3. إدخال اللاعب (المضيف)
            cur.execute("""
                INSERT INTO room_players (room_code, room_id, user_id, player_name, join_order, team)
                VALUES (%s, %s, %s, %s, 0, %s)
            """, (room_code, room_code, user_id, player_name, team_val))

            conn.commit()
        return {"success": True, "room_code": room_code}
    except Exception as e:
        print(f"Error creating domino room: {e}")
        return {"success": False, "msg": f"خطأ: {str(e)}"}
    finally: conn.close()

@app.post("/api/domino/set_team")
async def set_domino_team(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])
        team = data['team'] # 'A' or 'B'
        with conn.cursor() as cur:
            cur.execute("UPDATE room_players SET team = %s WHERE room_code = %s AND user_id = %s", (team, room_code, user_id))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@app.post("/api/domino/play")
async def domino_play_tile(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])
        tile = data['tile'] # [a, b]
        side = data.get('side', 'right') # 'left' or 'right'

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT game_data, status FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room or room['status'] != 'playing': return {"success": False, "msg": "اللعبة ليست جارية"}

            game_data = room['game_data']
            if isinstance(game_data, str): game_data = json.loads(game_data)
            
            if game_data['ordered_ids'][game_data['turn_index']] != user_id:
                return {"success": False, "msg": "ليس دورك"}

            hand = game_data['hands'][str(user_id)]
            if tile not in hand: return {"success": False, "msg": "لا تملك هذا الحجر"}

            board = game_data['board']
            if not board:
                board.append(tile)
            else:
                left_val = board[0][0]
                right_val = board[-1][1]

                if side == 'left':
                    if tile[1] == left_val:
                        board.insert(0, tile)
                    elif tile[0] == left_val:
                        board.insert(0, [tile[1], tile[0]])
                    else: return {"success": False, "msg": "الحجر لا يطابق الطرف الأيسر"}
                else: # right
                    if tile[0] == right_val:
                        board.append(tile)
                    elif tile[1] == right_val:
                        board.append([tile[1], tile[0]])
                    else: return {"success": False, "msg": "الحجر لا يطابق الطرف الأيمن"}

            # Remove from hand
            hand.remove(tile)

            # Refined scoring: winners get points equal to sum of opponents' hand pips (and partner's pips if applicable)
            if not hand:
                game_data['phase'] = 'round_end'
                # Find winner's team
                cur.execute("SELECT team FROM room_players WHERE room_code = %s AND user_id = %s", (room_code, user_id))
                winner_team = cur.fetchone()['team']

                # Calculate total pips remaining in other players' hands
                total_pips = 0
                for pid, phand in game_data['hands'].items():
                    # In Domino, usually you count all other hands if you win.
                    # In some variations, you count only opponents. We'll count all other remaining pips.
                    for t in phand:
                        total_pips += (t[0] + t[1])

                game_data['scores'][winner_team] += total_pips
                # Reset board for next round or handle game over logic could go here,
                # but for now we just mark phase and add score.
            else:
                # Check for stalemate (Board Locked)
                left_val = board[0][0]
                right_val = board[-1][1]

                can_anyone_move = False
                for pid, phand in game_data['hands'].items():
                    for t in phand:
                        if t[0] in [left_val, right_val] or t[1] in [left_val, right_val]:
                            can_anyone_move = True
                            break
                    if can_anyone_move: break

                # If no one can move and boneyard is empty, it's a stalemate
                if not can_anyone_move and not game_data['boneyard']:
                    game_data['phase'] = 'round_end'
                    # Calculate hand totals for everyone to find who has the least points
                    player_totals = {}
                    for pid, phand in game_data['hands'].items():
                        player_totals[pid] = sum(t[0] + t[1] for t in phand)

                    # Find player(s) with minimum points
                    min_pips = min(player_totals.values())
                    winners = [pid for pid, pips in player_totals.items() if pips == min_pips]

                    # In case of tie, some rules say no points or split. Let's give points to first winner's team found.
                    cur.execute("SELECT team FROM room_players WHERE room_code = %s AND user_id = %s", (room_code, int(winners[0])))
                    stalemate_winner_team = cur.fetchone()['team']

                    # Total pips from all hands
                    all_pips = sum(player_totals.values())
                    game_data['scores'][stalemate_winner_team] += all_pips
                else:
                    game_data['turn_index'] = (game_data['turn_index'] + 1) % len(game_data['ordered_ids'])

            cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@app.post("/api/domino/next_round")
async def domino_next_round(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT host_id, game_data FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if room['host_id'] != user_id: return {"success": False, "msg": "المضيف فقط يمكنه بدء جولة جديدة"}

            game_data = room['game_data']
            if isinstance(game_data, str): game_data = json.loads(game_data)
            if game_data['phase'] != 'round_end': return {"success": False, "msg": "الجولة لم تنتهِ بعد"}

            # Get players to reshuffle
            cur.execute("SELECT user_id, team FROM room_players WHERE room_code = %s", (room_code,))
            players = cur.fetchall()

            all_tiles = [[i, j] for i in range(7) for j in range(i, 7)]
            random.shuffle(all_tiles)

            hands = {}
            for p in players:
                hands[str(p['user_id'])] = [all_tiles.pop() for _ in range(7)]

            game_data['hands'] = hands
            game_data['boneyard'] = all_tiles
            game_data['board'] = []
            game_data['phase'] = 'playing'
            # Keep existing scores and ordered_ids
            # Rotate starter for variety or find double 6 again
            game_data['turn_index'] = (game_data.get('round_count', 0) + 1) % len(game_data['ordered_ids'])
            game_data['round_count'] = game_data.get('round_count', 0) + 1

            cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@app.post("/api/domino/draw")
async def domino_draw_tile(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT game_data FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            game_data = room['game_data']
            if isinstance(game_data, str): game_data = json.loads(game_data)

            if game_data['ordered_ids'][game_data['turn_index']] != user_id:
                return {"success": False, "msg": "ليس دورك"}

            if not game_data['boneyard']:
                # Pass turn if no more tiles
                game_data['turn_index'] = (game_data['turn_index'] + 1) % len(game_data['ordered_ids'])
                cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                conn.commit()
                return {"success": True, "msg": "لا يوجد أحجار للسحب، تم تمرير الدور"}

            tile = game_data['boneyard'].pop()
            game_data['hands'][str(user_id)].append(tile)

            cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@app.post("/api/domino/start")
async def start_domino_game_endpoint(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection error"}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT host_id, game_type FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room or room['game_type'] != 'domino':
                return {"success": False, "msg": "الغرفة غير موجودة أو ليست دومينو"}
            if room['host_id'] != user_id:
                return {"success": False, "msg": "فقط المضيف يمكنه بدء اللعبة"}

            cur.execute("SELECT user_id, player_name, team FROM room_players WHERE room_code = %s", (room_code,))
            players = cur.fetchall()
            n = len(players)

            if n not in [2, 4]:
                return {"success": False, "msg": "يجب أن يكون عدد اللاعبين 2 أو 4"}

            # توزيع الفرق تلقائياً إذا لم تكن موزعة بشكل صحيح
            # نحتاج تقسيم اللاعبين لمجموعتين متساويتين
            team_a = []
            team_b = []
            for i, p in enumerate(players):
                if i % 2 == 0: team_a.append(p)
                else: team_b.append(p)

            # تحديث الفرق في قاعدة البيانات لضمان الاستمرارية (استخدام 0 و 1 لأن العمود من نوع integer)
            for p in team_a:
                cur.execute("UPDATE room_players SET team = %s WHERE room_code = %s AND user_id = %s", (0, room_code, p['user_id']))
            for p in team_b:
                cur.execute("UPDATE room_players SET team = %s WHERE room_code = %s AND user_id = %s", (1, room_code, p['user_id']))

            # إنشاء وتوزيع الأحجار
            all_tiles = [[i, j] for i in range(7) for j in range(i, 7)]
            random.shuffle(all_tiles)

            hands = {}
            for p in players:
                hands[str(p['user_id'])] = [all_tiles.pop() for _ in range(7)]

            # ترتيب اللعب (دائري: فريق A ثم B ثم A ثم B)
            # إذا 4 لاعبين: A1, B1, A2, B2
            # إذا 2 لاعبين: A1, B1
            ordered_players = []
            if n == 4:
                ordered_players = [team_a[0], team_b[0], team_a[1], team_b[1]]
            else:
                ordered_players = [team_a[0], team_b[0]]

            # من يبدأ؟ (صاحب أعلى دبل، أو الدبل 6)
            starter_id = ordered_players[0]['user_id']
            max_double = -1
            for p_id, hand in hands.items():
                for tile in hand:
                    if tile[0] == tile[1] and tile[0] > max_double:
                        max_double = tile[0]
                        starter_id = int(p_id)

            game_data = {
                "hands": hands,
                "boneyard": all_tiles,
                "board": [],
                "turn_index": next(i for i, p in enumerate(ordered_players) if p['user_id'] == starter_id),
                "ordered_ids": [p['user_id'] for p in ordered_players],
                "scores": {"A": 0, "B": 0},
                "history": [],
                "phase": "playing"
            }

            cur.execute("UPDATE rooms SET status = 'playing', game_data = %s WHERE room_code = %s",
                        (json.dumps(game_data), room_code))
            conn.commit()

        return {"success": True}
    except Exception as e:
        print(f"Error starting domino: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

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
    category = str(data.get('category', 'أكلات'))
    win_limit = 10
    try:
        win_limit = int(data.get('win_limit', 10))
    except:
        pass

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
                VALUES (%s, %s, %s, %s, 'waiting', %s, %s)
            """, (room_code, room_code, user_id, user_id, category, win_limit))

            cur.execute("""
                INSERT INTO room_players (room_code, room_id, user_id, player_name, is_ready, join_order, score, vote_limit, vote_cat)
                VALUES (%s, %s, %s, %s, TRUE, 1, 0, %s, %s)
                ON CONFLICT (room_code, user_id) DO UPDATE
                SET is_ready = TRUE, join_order = 1, player_name = EXCLUDED.player_name,
                    vote_limit = EXCLUDED.vote_limit, vote_cat = EXCLUDED.vote_cat
            """, (room_code, room_code, user_id, player_name, win_limit, category))

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
            # 1. فحص الأعمدة المتاحة في جدول الغرف بطريقة متوافقة مع RealDictCursor
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'rooms'")
            room_cols = [r['column_name'] for r in cur.fetchall()]
            id_col = 'room_code' if 'room_code' in room_cols else 'room_id'

            cur.execute(f"SELECT status, game_type, max_players FROM rooms WHERE {id_col} = %s", (room_code,))
            room = cur.fetchone()
            if not room: return {"success": False, "msg": "الغرفة غير موجودة"}

            game_type = room.get('game_type', 'spy')
            status = room['status']

            # السماح بالانضمام إذا كانت الحالة 'waiting' (برا السالفة) أو 'lobby' (دومينو)
            is_open = (status == 'waiting' or status == 'lobby')

            # 2. فحص إذا كان اللاعب موجود مسبقاً
            cur.execute(f"SELECT join_order FROM room_players WHERE ({id_col} = %s) AND user_id = %s", (room_code, user_id))
            row = cur.fetchone()

            if not row and not is_open:
                return {"success": False, "msg": "اللعبة بدأت بالفعل ولا يمكنك الانضمام كلاعب جديد"}

            if not row:
                # التحقق من العدد الأقصى للاعبين
                cur.execute(f"SELECT COUNT(*) as count FROM room_players WHERE {id_col} = %s", (room_code,))
                current_count = cur.fetchone()['count']
                max_p = room.get('max_players') or (4 if game_type == 'domino' else 10)

                if current_count >= max_p:
                    return {"success": False, "msg": f"عذراً، الغرفة ممتلئة (الحد الأقصى {max_p} لاعبين)"}

                # تحديد الترتيب القادم
                cur.execute(f"SELECT COALESCE(MAX(join_order), 0) + 1 as next_order FROM room_players WHERE {id_col} = %s", (room_code,))
                next_order = cur.fetchone()['next_order']

                # 3. فحص أعمدة جدول اللاعبين ونوعها (خاصة الفريق)
                cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'room_players'")
                p_cols_res = cur.fetchall()
                p_cols_info = {r['column_name']: r['data_type'] for r in p_cols_res}

                team_val = None
                if game_type == 'domino' and 'team' in p_cols_info:
                    # توزيع اللاعبين على فريقين (A, B) أو (0, 1) آلياً
                    is_int = 'int' in p_cols_info['team'].lower()
                    if is_int:
                        team_val = int(current_count % 2)
                    else:
                        team_val = 'A' if current_count % 2 == 0 else 'B'

                player_vals = {
                    'room_id': room_code,
                    'room_code': room_code,
                    'user_id': user_id,
                    'player_name': player_name,
                    'join_order': next_order,
                    'team': team_val,
                    'is_ready': True
                }

                valid_player_data = {k: v for k, v in player_vals.items() if k in p_cols_info}
                cols_str = ", ".join(valid_player_data.keys())
                placeholders = ", ".join(["%s"] * len(valid_player_data))

                cur.execute(f"INSERT INTO room_players ({cols_str}) VALUES ({placeholders})", list(valid_player_data.values()))
            else:
                # تحديث اسم اللاعب إذا عاد للانضمام
                cur.execute(f"UPDATE room_players SET player_name = %s WHERE {id_col} = %s AND user_id = %s",
                            (player_name, room_code, user_id))

            conn.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error in join_room: {e}")
        return {"success": False, "msg": f"خطأ تقني: {str(e)}"}
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
        vote_type = data['type'] # 'limit' or 'cat'
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
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT host_id FROM rooms WHERE room_code = %s", (room_code,))
            r = cur.fetchone()
            if not r: return {"success": False, "msg": "الغرفة غير موجودة"}
            if r['host_id'] != int(data['user_id']): return {"success": False, "msg": "فقط المضيف يمكنه البدء"}

            # التأكد من عدد اللاعبين
            cur.execute("SELECT COUNT(*) FROM room_players WHERE room_code = %s", (room_code,))
            if cur.fetchone()['count'] < 3: return {"success": False, "msg": "يجب وجود 3 لاعبين على الأقل"}

            # حساب نتائج التصويت في اللوبي
            # 1. نقاط الفوز
            cur.execute("SELECT vote_limit, COUNT(*) as c FROM room_players WHERE room_code = %s AND vote_limit IS NOT NULL GROUP BY vote_limit ORDER BY c DESC LIMIT 1", (room_code,))
            res_limit = cur.fetchone()

            # 2. الفئة
            cur.execute("SELECT vote_cat, COUNT(*) as c FROM room_players WHERE room_code = %s AND vote_cat IS NOT NULL GROUP BY vote_cat ORDER BY c DESC LIMIT 1", (room_code,))
            res_cat = cur.fetchone()

            if res_limit or res_cat:
                win_limit = res_limit['vote_limit'] if res_limit else 10
                category = res_cat['vote_cat'] if res_cat else "أكلات"
                cur.execute("UPDATE rooms SET win_limit = %s, category = %s, status = 'roles_prep' WHERE room_code = %s", (win_limit, category, room_code))
            else:
                # If no one voted in lobby, keep the room's preset settings (chosen at creation)
                cur.execute("UPDATE rooms SET status = 'roles_prep' WHERE room_code = %s", (room_code,))

            conn.commit()

        # البدء الفعلي (توزيع الأدوار)
        await prepare_round(room_code)

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
        is_lobby = data.get('is_lobby', False)

        should_prepare = False
        with conn.cursor() as cur:
            if vote_type == 'limit':
                cur.execute("UPDATE room_players SET vote_limit = %s WHERE room_code = %s AND user_id = %s", (int(val), room_code, user_id))
            else:
                cur.execute("UPDATE room_players SET vote_cat = %s WHERE room_code = %s AND user_id = %s", (val, room_code, user_id))

            # إذا لم نكن في اللوبي، نكمل المنطق القديم للانتقال التلقائي
            if not is_lobby:
                cur.execute(f"SELECT COUNT(*) FROM room_players WHERE room_code = %s AND vote_{vote_type} IS NULL", (room_code,))
                if cur.fetchone()[0] == 0:
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

        if should_prepare and not is_lobby:
            conn.close()
            conn = None
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

            other = [w for w in words if w != correct]
            guesses = random.sample(other, min(len(other), 6)) + [correct]
            random.shuffle(guesses)

            # Initial asker is the first active player
            current_asker = active_players[0]

            # Generate automatic sequence if needed (everyone asks everyone)
            # 1 asks 2, 2 asks 3... n asks 1, then 1 asks 3, etc.
            auto_seq = []
            p_ids = [p['user_id'] for p in active_players]
            n = len(p_ids)
            for shift in range(1, n):
                for i in range(n):
                    asker_id = p_ids[i]
                    ans_id = p_ids[(i + shift) % n]
                    auto_seq.append({'asker_id': asker_id, 'ans_id': ans_id})

            dist_mode = room.get('distribution_mode', 'auto')
            # إذا كان عدد اللاعبين 3، نجعل نظام الأسئلة اختيارياً للكل بدلاً من التتابع التلقائي
            if len(active_players) == 3:
                dist_mode = 'manual'

            game_data = {
                "word": correct,
                "spy_id": spy_id,
                "q_seq": [], # History of completed questions
                "auto_seq": auto_seq, # Pre-calculated sequence
                "current_seq_idx": 0,
                "distribution_mode": dist_mode,
                "current_asker_id": current_asker['user_id'],
                "current_asker_name": current_asker['player_name'],
                "ready_to_vote": [], # List of user_ids who clicked "Vote"
                "current_q": None, # Ongoing question {ans_id, ans_name, question, answer, status}
                "guesses": guesses,
                "messages": [],
                "phase_start": time.time(),
                "phase_timeout": 0
            }

            cur.execute("UPDATE rooms SET status = 'playing_questions', secret_word = %s, spy_id = %s, game_data = %s WHERE room_code = %s",
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
            else:
                # Always go to spy_reveal phase to let the spy guess the word
                game_data['phase_start'] = time.time()
                cur.execute("UPDATE rooms SET status = 'spy_reveal', game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))

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
                game_data = room.get('game_data') or {}
                current_asker_id = game_data.get('current_asker_id')
                current_q = game_data.get('current_q')
                phase_start = game_data.get('phase_start')

                # Fetch question timeout from settings or default to 30
                cur.execute("SELECT value FROM settings WHERE key = 'question_timeout'")
                q_timeout_row = cur.fetchone()
                q_timeout = int(q_timeout_row['value']) if q_timeout_row else 30

                # Check for absolute timeout to skip turns for absent players
                if phase_start:
                    elapsed = time.time() - phase_start
                    if elapsed > q_timeout:
                        changed = True
                        if not current_q:
                            # Asker didn't choose a target
                            cur.execute("UPDATE room_players SET yellow_cards = yellow_cards + 1 WHERE room_code = %s AND user_id = %s", (room_code, current_asker_id))
                            # Move turn to next player
                            cur.execute("SELECT user_id, player_name FROM room_players WHERE room_code = %s AND red_card = FALSE ORDER BY join_order ASC", (room_code,))
                            active_players = cur.fetchall()
                            if active_players:
                                curr_idx = next((i for i, p in enumerate(active_players) if p['user_id'] == current_asker_id), 0)
                                next_asker = active_players[(curr_idx + 1) % len(active_players)]

                                game_data['current_asker_id'] = next_asker['user_id']
                                game_data['current_asker_name'] = next_asker['player_name']
                            game_data['phase_start'] = time.time()
                        else:
                            # Asking or Answering timeout
                            target_id = current_q['asker_id'] if current_q['status'] == 'asking' else current_q['ans_id']
                            cur.execute("UPDATE room_players SET yellow_cards = yellow_cards + 1 WHERE room_code = %s AND user_id = %s", (room_code, target_id))

                            # Cancel current question and move turn to next asker
                            cur.execute("SELECT user_id, player_name FROM room_players WHERE room_code = %s AND red_card = FALSE ORDER BY join_order ASC", (room_code,))
                            active_players = cur.fetchall()
                            if active_players:
                                curr_idx = next((i for i, p in enumerate(active_players) if p['user_id'] == current_asker_id), 0)
                                next_asker = active_players[(curr_idx + 1) % len(active_players)]

                                game_data['current_asker_id'] = next_asker['user_id']
                                game_data['current_asker_name'] = next_asker['player_name']
                            game_data['current_q'] = None
                            game_data['phase_start'] = time.time()

                        # Check for red cards (2 yellows = red)
                        cur.execute("UPDATE room_players SET red_card = TRUE WHERE room_code = %s AND yellow_cards >= 2", (room_code,))

            elif status == 'spy_reveal':
                phase_start = game_data.get('phase_start')
                if phase_start and (time.time() - phase_start > 15):
                    # Auto-timeout for spy guess
                    if 'spy_guess' not in game_data:
                        game_data['spy_guess'] = "لم يختبر (انتهى الوقت)"
                    cur.execute("UPDATE rooms SET status = 'result', game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                    changed = True

            if changed:
                cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                conn.commit()
                # Re-fetch room if changed
                cur.execute("SELECT * FROM rooms WHERE room_code = %s", (room_code,))
                room = cur.fetchone()

            cur.execute("SELECT user_id, player_name, is_ready, score, yellow_cards, red_card, vote_limit, vote_cat, said_uno FROM room_players WHERE room_code = %s ORDER BY join_order ASC, user_id ASC", (room_code,))
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
                    cur_new.execute("SELECT user_id, player_name, is_ready, score, yellow_cards, red_card, vote_limit, vote_cat, said_uno FROM room_players WHERE room_code = %s ORDER BY join_order ASC, user_id ASC", (room_code,))
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
                    cur_new.execute("SELECT user_id, player_name, is_ready, score, yellow_cards, red_card, vote_limit, vote_cat, said_uno FROM room_players WHERE room_code = %s ORDER BY join_order ASC, user_id ASC", (room_code,))
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
                if status in ['voting_limit', 'voting_cat', 'voting_spy', 'spy_reveal']:
                    time_left = max(0, int(15 - elapsed))
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

            elif action == "choose_target":
                target_id = int(data['target_id'])
                target_name = data['target_name']

                # Check if it's manual mode and host or it's the asker's turn
                is_host = room['host_id'] == int(user_id)
                can_choose = (game_data.get('distribution_mode') == 'manual' and is_host) or \
                            (game_data.get('distribution_mode') == 'auto' and game_data.get('current_asker_id') == user_id)

                if can_choose and not game_data.get('current_q'):
                    game_data['current_q'] = {
                        "asker_id": game_data['current_asker_id'],
                        "asker_name": game_data['current_asker_name'],
                        "ans_id": target_id, "ans_name": target_name,
                        "status": "asking", "question": "", "answer": ""
                    }
                    game_data['phase_start'] = time.time()
                    cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                conn.commit()

            elif action == "toggle_vote_ready":
                if 'ready_to_vote' not in game_data: game_data['ready_to_vote'] = []
                if user_id not in game_data['ready_to_vote']:
                    game_data['ready_to_vote'].append(user_id)

                # Check if everyone is ready to vote
                cur.execute("SELECT user_id FROM room_players WHERE room_code = %s AND red_card = FALSE", (room_code,))
                active_ids = [p['user_id'] for p in cur.fetchall()]

                all_ready = True
                for aid in active_ids:
                    if aid not in game_data['ready_to_vote']:
                        all_ready = False; break

                if all_ready:
                    game_data['phase_start'] = time.time()
                    cur.execute("UPDATE rooms SET status = 'voting_spy', game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                else:
                    # If it was my turn to ask, pass it randomly
                    if game_data.get('current_asker_id') == user_id and not game_data.get('current_q'):
                        others = [aid for aid in active_ids if aid not in game_data['ready_to_vote']]
                        if others:
                            new_asker_id = random.choice(others)
                            cur.execute("SELECT player_name FROM room_players WHERE user_id = %s", (new_asker_id,))
                            game_data['current_asker_id'] = new_asker_id
                            game_data['current_asker_name'] = cur.fetchone()['player_name']

                    cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                conn.commit()

            elif action == "submit_question":
                # Check if red carded
                cur.execute("SELECT red_card FROM room_players WHERE room_code = %s AND user_id = %s", (room_code, user_id))
                res = cur.fetchone()
                if res and res['red_card']: return {"success": False, "msg": "أنت مستبعد (كرت أحمر)"}

                curr_q = game_data.get('current_q')
                if curr_q and curr_q['asker_id'] == user_id and curr_q['status'] == 'asking':
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

                curr_q = game_data.get('current_q')
                if curr_q and curr_q['ans_id'] == user_id and curr_q['status'] == 'answering':
                    curr_q['answer'] = data['text']
                    curr_q['status'] = 'done'

                    # Add to history
                    if 'q_seq' not in game_data: game_data['q_seq'] = []
                    game_data['q_seq'].append(curr_q)
                    game_data['current_q'] = None

                    # Logic for next asker
                    if game_data.get('distribution_mode') == 'auto':
                        # Advance in pre-calculated sequence
                        game_data['current_seq_idx'] = game_data.get('current_seq_idx', 0) + 1
                        auto_seq = game_data.get('auto_seq', [])

                        if game_data['current_seq_idx'] < len(auto_seq):
                            next_pair = auto_seq[game_data['current_seq_idx']]
                            game_data['current_asker_id'] = next_pair['asker_id']
                            cur.execute("SELECT player_name FROM room_players WHERE user_id = %s", (next_pair['asker_id'],))
                            game_data['current_asker_name'] = cur.fetchone()['player_name']

                            # Automatically set the target (answerer) for auto mode
                            cur.execute("SELECT player_name FROM room_players WHERE user_id = %s", (next_pair['ans_id'],))
                            ans_name = cur.fetchone()['player_name']
                            game_data['current_q'] = {
                                "asker_id": next_pair['asker_id'], "asker_name": game_data['current_asker_name'],
                                "ans_id": next_pair['ans_id'], "ans_name": ans_name,
                                "status": "asking", "question": "", "answer": ""
                            }
                        else:
                            # End of sequence, maybe go to voting or loop?
                            # For now, let it be manual or just keep last asker
                            pass
                    else:
                        # Manual mode: Next asker is the one who just answered
                        next_asker_id = curr_q['ans_id']
                        next_asker_name = curr_q['ans_name']

                        # If the next asker already opted to vote, pick a random person who hasn't
                        if next_asker_id in game_data.get('ready_to_vote', []):
                            cur.execute("SELECT user_id, player_name FROM room_players WHERE room_code = %s AND red_card = FALSE", (room_code,))
                            active_players = cur.fetchall()
                            others = [p for p in active_players if p['user_id'] not in game_data['ready_to_vote']]
                            if others:
                                chosen = random.choice(others)
                                next_asker_id = chosen['user_id']
                                next_asker_name = chosen['player_name']
                            else:
                                game_data['phase_start'] = time.time()
                                cur.execute("UPDATE rooms SET status = 'voting_spy', game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                                conn.commit()
                                return {"success": True}

                        game_data['current_asker_id'] = next_asker_id
                        game_data['current_asker_name'] = next_asker_name

                    game_data['phase_start'] = time.time()
                    cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                conn.commit()

            elif action == "adjust_timer":
                # Only host can adjust timer mid-game
                if room['host_id'] == user_id:
                    new_time = int(data['new_time'])
                    # We adjust the phase_start to "add" or "subtract" time from the current phase
                    # Logic: Current time left = q_timeout - (now - phase_start)
                    # We want: Current time left = new_time
                    # So: new_time = q_timeout - (now - new_phase_start)
                    # new_phase_start = now - q_timeout + new_time

                    cur.execute("SELECT value FROM settings WHERE key = 'question_timeout'")
                    q_timeout_row = cur.fetchone()
                    q_timeout = int(q_timeout_row['value']) if q_timeout_row else 30

                    game_data['phase_start'] = time.time() - q_timeout + new_time
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
            category = data.get('category')
            raw_word = data.get('word', '')
            # تقسيم النص إلى أسطر وتصفيف الكلمات الفارغة
            words = [w.strip() for w in raw_word.split('\n') if w.strip()]

            if not words:
                return {"success": False, "msg": "لم يتم إدخال كلمات صالحة"}

            for w in words:
                cur.execute("INSERT INTO words (category, word) VALUES (%s, %s)", (category, w))
            conn.commit()
        return {"success": True, "added_count": len(words)}
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
            # ترتيب مباشر في قاعدة البيانات مع حد أقصى لتحسين السرعة
            cur.execute("SELECT user_id, username_key, player_name, total_wins FROM users ORDER BY total_wins DESC LIMIT 200")
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
            # تم تعديل الاستعلام ليشمل id و image_url و display_order
            cur.execute("SELECT id, name, image_url, display_order FROM categories ORDER BY display_order ASC, name ASC")
            cats = cur.fetchall()

            # If categories table is empty, seed it
            if not cats:
                default_cats = list(CATEGORIES.keys())
                for i, c in enumerate(default_cats):
                    cur.execute("INSERT INTO categories (name, display_order) VALUES (%s, %s) ON CONFLICT DO NOTHING", (c, i))
                conn.commit()
                cur.execute("SELECT id, name, image_url, display_order FROM categories ORDER BY display_order ASC, name ASC")
                cats = cur.fetchall()

            # Migrate words if words table is empty
            cur.execute("SELECT COUNT(*) FROM words")
            if cur.fetchone()['count'] == 0:
                for cat, word_list in CATEGORIES.items():
                    for word in word_list:
                        cur.execute("INSERT INTO words (category, word) VALUES (%s, %s) ON CONFLICT DO NOTHING", (cat, word))
                conn.commit()

            return cats
    except Exception as e:
        print(f"Error in get_categories: {e}")
        return []
    finally:
        if conn: conn.close()

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
        :root {
            --primary: #00d2ff;
            --bg: #050505;
            --card: rgba(25, 25, 35, 0.95);
            --accent: #00ff88;
            --error: #ff2d55;
            --success: #00ff88;
            --neon-blue: #00d2ff;
            --neon-purple: #9d50bb;
        }
        body {
            font-family: 'Cairo', sans-serif;
            background: radial-gradient(circle at center, #1a1a2e 0%, #050505 100%);
            color: white;
            margin: 0; padding: 0;
            min-height: 100vh;
            display: flex; justify-content: center; align-items: flex-start;
            direction: rtl; overflow-x: hidden;
            padding-top: 20px;
        }
        /* Scrollbar Styling */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: rgba(0,0,0,0.1); border-radius: 10px; }
        ::-webkit-scrollbar-thumb { background: rgba(0, 210, 255, 0.3); border-radius: 10px; border: 2px solid transparent; background-clip: content-box; }
        ::-webkit-scrollbar-thumb:hover { background: var(--primary); border-radius: 10px; border: 2px solid transparent; background-clip: content-box; }

        .flex-center { width: 100%; display: flex; justify-content: center; align-items: center; min-height: 100vh; flex-direction: column; }
        .container { width: 100%; max-width: 100%; text-align: center; padding: 10px; box-sizing: border-box; }
        .card {
            background: var(--card);
            padding: 20px 12px;
            border-radius: 28px;
            box-shadow: 0 0 30px rgba(0, 210, 255, 0.2);
            border: 1px solid rgba(0, 210, 255, 0.4);
            backdrop-filter: blur(15px);
            animation: fadeIn 0.3s ease;
            width: 98%;
            max-width: 500px;
            margin: 0 auto;
            box-sizing: border-box;
            position: relative;
        }
        /* Admin Dashboard Improvements */
        .admin-wide-card {
            max-width: none !important;
            width: 100% !important;
            padding: 30px 15px !important;
            margin: 0 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            min-height: 100vh;
        }
        .admin-content-box {
            background: rgba(0,0,0,0.3);
            padding: 30px;
            border-radius: 25px;
            margin: 25px 0;
            text-align: right;
            width: 100%;
            box-sizing: border-box;
        }
        .admin-section-title {
            color: var(--accent);
            border-bottom: 2px solid var(--primary);
            padding-bottom: 8px;
            margin-bottom: 20px;
            font-size: 1.2rem;
        }
        .admin-setting-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
            gap: 15px;
            flex-wrap: wrap;
        }
        .admin-input-group {
            display: flex;
            gap: 10px;
            flex: 1;
            width: 100%;
        }
        .admin-input-group input {
            flex: 1;
            margin: 0 !important;
        }
        .admin-save-btn {
            width: 100px !important;
            background: var(--success) !important;
            margin: 0 !important;
            padding: 8px !important;
        }
        .admin-upload-box {
            display: flex;
            flex-direction: column;
            gap: 10px;
            width: 100%;
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 12px;
        }
        .admin-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            width: 100%;
        }
        .admin-item-card {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 15px;
            border: 1px solid rgba(255,255,255,0.1);
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .word-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }
        .word-chip {
            background: rgba(0, 210, 255, 0.1);
            border: 1px solid rgba(0, 210, 255, 0.3);
            padding: 8px 12px;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.95rem;
        }
        .card::before {
            content: '';
            position: absolute;
            top: -2px; left: -2px; right: -2px; bottom: -2px;
            background: linear-gradient(45deg, var(--primary), transparent, var(--accent));
            z-index: -1;
            border-radius: 26px;
            opacity: 0.3;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideIn { from { transform: translateX(100px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .reveal-text {
            animation: pop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            text-shadow: 0 0 10px var(--primary);
        }
        @keyframes pop { 0% { transform: scale(0.5); } 100% { transform: scale(1); } }
        @keyframes bell-ring {
            0% { transform: rotate(0); }
            10% { transform: rotate(15deg); }
            20% { transform: rotate(-15deg); }
            30% { transform: rotate(10deg); }
            40% { transform: rotate(-10deg); }
            50% { transform: rotate(5deg); }
            60% { transform: rotate(-5deg); }
            100% { transform: rotate(0); }
        }
        .bell-btn {
            position: relative;
            background: rgba(255,255,255,0.1);
            border: none;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            font-size: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            margin: 0 auto 20px auto;
            transition: all 0.3s ease;
        }
        .bell-btn.dance {
            animation: bell-ring 1s infinite;
            background: rgba(241, 196, 15, 0.2);
            box-shadow: 0 0 15px rgba(241, 196, 15, 0.3);
        }
        .bell-badge {
            position: absolute;
            top: 5px;
            right: 5px;
            background: #ff7675;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            border: 2px solid #1b1464;
            display: none;
        }
        .bell-btn.dance .bell-badge {
            display: block;
        }
        .announcement-item {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 12px;
            margin-bottom: 10px;
            text-align: right;
            border-right: 4px solid var(--accent);
        }
        .announcement-date {
            font-size: 10px;
            color: #9aa0b4;
            margin-top: 5px;
        }
        @keyframes bell-ring {
            0% { transform: rotate(0); }
            10% { transform: rotate(15deg); }
            20% { transform: rotate(-15deg); }
            30% { transform: rotate(10deg); }
            40% { transform: rotate(-10deg); }
            50% { transform: rotate(5deg); }
            60% { transform: rotate(-5deg); }
            100% { transform: rotate(0); }
        }
        .bell-btn {
            position: relative;
            background: rgba(255,255,255,0.1);
            border: none;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            font-size: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            margin: 0 auto 20px auto;
            transition: all 0.3s ease;
        }
        .bell-btn.dance {
            animation: bell-ring 1s infinite;
            background: rgba(241, 196, 15, 0.2);
            box-shadow: 0 0 15px rgba(241, 196, 15, 0.3);
        }
        .bell-badge {
            position: absolute;
            top: 5px;
            right: 5px;
            background: var(--error);
            width: 12px;
            height: 12px;
            border-radius: 50%;
            border: 2px solid #1b1464;
            display: none;
        }
        .bell-btn.dance .bell-badge {
            display: block;
        }
        .announcement-item {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 12px;
            margin-bottom: 10px;
            text-align: right;
            border-right: 4px solid var(--accent);
        }
        .announcement-date {
            font-size: 10px;
            color: #9aa0b4;
            margin-top: 5px;
        }
        h1 {
            font-weight: 900;
            color: white;
            text-shadow: 0 0 15px var(--primary);
            margin-bottom: 25px;
            font-size: 32px;
            letter-spacing: 1px;
        }
        input, select {
            width: 100%;
            padding: 15px;
            margin: 10px 0;
            border-radius: 15px;
            border: 1px solid rgba(0, 210, 255, 0.2);
            background: rgba(0,0,0,0.5);
            color: white;
            font-size: 16px;
            box-sizing: border-box;
            outline: none;
            transition: 0.3s;
        }
        input:focus { border-color: var(--primary); box-shadow: 0 0 10px rgba(0, 210, 255, 0.4); }
        button {
            width: 100%;
            padding: 16px;
            margin: 12px 0;
            border-radius: 18px;
            border: none;
            background: linear-gradient(90deg, #00d2ff, #3a7bd5);
            color: white;
            font-weight: bold;
            cursor: pointer;
            font-size: 18px;
            transition: 0.3s;
            box-shadow: 0 4px 15px rgba(0, 210, 255, 0.3);
            text-transform: uppercase;
        }
        button:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(0, 210, 255, 0.5);
            filter: brightness(1.1);
        }
        button:active { transform: scale(0.98); }
        button:disabled { opacity: 0.4; cursor: not-allowed; transform: none !important; }
        .btn-yellow {
            background: linear-gradient(90deg, #f1c40f, #f39c12) !important;
            color: #050505 !important;
            box-shadow: 0 4px 15px rgba(241, 196, 15, 0.3) !important;
        }
        .btn-yellow:hover { box-shadow: 0 6px 20px rgba(241, 196, 15, 0.5) !important; }
        .sidebar {
            position: fixed;
            right: -280px;
            top: 0;
            width: 280px;
            height: 100vh;
            background: rgba(10, 10, 20, 0.95);
            backdrop-filter: blur(15px);
            transition: 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 1000;
            padding: 30px 20px;
            box-sizing: border-box;
            border-left: 1px solid var(--primary);
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .sidebar::-webkit-scrollbar { width: 3px; }
        .sidebar::-webkit-scrollbar-thumb { background: var(--primary); }
        .sidebar.open { right: 0; box-shadow: -10px 0 30px rgba(0,0,0,0.5); }
        .menu-btn {
            position: fixed;
            right: 20px;
            top: 20px;
            font-size: 24px;
            cursor: pointer;
            z-index: 1001;
            background: rgba(255,255,255,0.05);
            width: 50px;
            height: 50px;
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            backdrop-filter: blur(5px);
            border: 1px solid rgba(255,255,255,0.1);
            transition: 0.3s;
        }
        .menu-btn:hover { background: var(--primary); color: #050505; }
        .vote-item {
            background: rgba(255,255,255,0.05);
            padding: 18px;
            margin: 10px 0;
            border-radius: 20px;
            cursor: pointer;
            transition: 0.3s;
            font-weight: bold;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .vote-item:hover {
            background: rgba(0, 210, 255, 0.1);
            border-color: var(--primary);
            transform: scale(1.02);
        }
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
        .score-item {
            display: flex;
            justify-content: space-between;
            background: rgba(255,255,255,0.03);
            padding: 12px 20px;
            border-radius: 15px;
            margin: 8px 0;
            border: 1px solid rgba(255,255,255,0.05);
            transition: 0.3s;
        }
        .score-item:hover {
            background: rgba(255,255,255,0.07);
            border-color: var(--primary);
        }
        .cat-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin: 10px 0;
            max-height: 60vh;
            overflow-y: auto;
            padding: 5px;
        }
        .cat-card {
            background: rgba(255,255,255,0.07);
            border-radius: 20px;
            padding: 8px;
            cursor: pointer;
            border: 2px solid rgba(255,255,255,0.1);
            transition: 0.3s;
            display: flex;
            flex-direction: column;
            align-items: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.4);
        }
        .cat-card:hover {
            transform: scale(1.03);
            border-color: var(--primary);
        }
        .cat-card.selected {
            border-color: var(--accent);
            background: rgba(0, 255, 136, 0.1);
        }
        .cat-card img {
            width: 100%;
            height: 140px;
            object-fit: cover;
            border-radius: 15px;
            margin-bottom: 8px;
        }
        .cat-card span {
            font-weight: bold;
            font-size: 16px;
        }
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
        .cat-card span { font-size: 10px; font-weight: bold; text-align: center; line-height: 1.2; }
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
            height: 700px; /* زيادة الطول ليأخذ مساحة أكبر من الشاشة */
            max-height: 85vh;
            text-align: right;
            direction: rtl;
            background: linear-gradient(180deg, rgba(0, 210, 255, 0.03) 0%, rgba(0, 0, 0, 0) 100%);
            border-radius: 20px;
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
            background: rgba(0, 0, 0, 0.4);
            border-radius: 18px;
            border: 1px solid rgba(0, 210, 255, 0.1);
            box-shadow: inset 0 4px 15px rgba(0,0,0,0.6);
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
            padding: 12px 16px;
            border-radius: 15px;
            font-size: 15px;
            line-height: 1.5;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            animation: pop 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.15);
            position: relative;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .bubble-asker {
            background: linear-gradient(135deg, rgba(0, 210, 255, 0.1), rgba(58, 123, 213, 0.2));
            align-self: flex-start;
            border-bottom-right-radius: 2px;
            border-color: rgba(0, 210, 255, 0.4);
        }
        .bubble-answerer {
            background: linear-gradient(135deg, rgba(0, 255, 136, 0.1), rgba(0, 189, 104, 0.2));
            align-self: flex-end;
            border-bottom-left-radius: 2px;
            border-color: rgba(0, 255, 136, 0.4);
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
            border-top: 1px solid rgba(0, 210, 255, 0.2);
            padding-top: 15px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .qa-timer-badge {
            align-self: center;
            font-size: 14px;
            font-weight: bold;
            color: var(--neon-blue);
            background: rgba(0, 210, 255, 0.1);
            padding: 6px 15px;
            border-radius: 10px;
            border: 1px solid var(--primary);
            box-shadow: 0 0 10px rgba(0, 210, 255, 0.2);
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

        /* Domino Styles */
        .domino-tile {
            background: linear-gradient(145deg, #ffffff, #f1efe9);
            color: #2c3e50;
            width: 44px;
            height: 84px;
            border-radius: 8px;
            display: inline-flex;
            flex-direction: column;
            border: 1px solid #d5d0c5;
            box-shadow: 0 4px 6px rgba(0,0,0,0.15), 0 1px 3px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);
            position: relative;
            user-select: none;
            flex-shrink: 0;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            align-items: center;
        }
        .domino-tile.double {
            width: 44px;
            height: 84px;
            flex-direction: column;
        }
        .domino-half {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
            font-size: 20px;
            font-family: 'Cairo', sans-serif;
            text-shadow: 1px 1px 0px rgba(255,255,255,0.8);
        }
        .domino-line {
            width: 80%;
            height: 2px;
            background: #b2bec3;
            margin: 0 auto;
            position: relative;
        }
        /* نقطة نحاسية كلاسيكية في منتصف الخط الفاصل للأحجار الفخمة */
        .domino-line::after {
            content: '';
            position: absolute;
            width: 6px;
            height: 6px;
            background: #d4af37; /* لون ذهبي نحاسي */
            border-radius: 50%;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            box-shadow: 0 1px 2px rgba(0,0,0,0.4);
        }
        /* على الطاولة فقط: الحجر العادي يكون نائم (بالعرض) والدبل يكون واقف */
        #domino-board .domino-tile {
            flex-direction: row;
            width: 84px;
            height: 44px;
            box-shadow: 0 6px 12px rgba(0,0,0,0.25), 0 2px 4px rgba(0,0,0,0.15);
        }
        #domino-board .domino-tile .domino-line {
            width: 2px;
            height: 80%;
            margin: auto 0;
        }
        #domino-board .domino-tile.double {
            flex-direction: column;
            width: 44px;
            height: 84px;
        }
        #domino-board .domino-tile.double .domino-line {
            width: 80%;
            height: 2px;
            margin: 0 auto;
        }
        .domino-tile.playable {
            cursor: pointer;
            border-color: #00ffaa;
            box-shadow: 0 0 12px rgba(0, 255, 170, 0.7), inset 0 0 6px rgba(0, 255, 170, 0.4);
            animation: pulse-glow-domino 1.2s infinite alternate;
        }
        @keyframes pulse-glow-domino {
            from { box-shadow: 0 0 6px rgba(0, 255, 170, 0.4), inset 0 0 4px rgba(0, 255, 170, 0.2); border-color: #00cc88; }
            to { box-shadow: 0 0 18px rgba(0, 255, 170, 0.9), inset 0 0 10px rgba(0, 255, 170, 0.6); border-color: #00ffaa; }
        }
        .domino-tile.playable:hover {
            transform: translateY(-8px) scale(1.08);
            border-color: #00ffaa;
            box-shadow: 0 0 24px rgba(0, 255, 170, 1), inset 0 0 12px rgba(0, 255, 170, 0.8);
            z-index: 10;
        }
        #domino-board {
            perspective: 1000px;
        }
        .domino-tile {
            animation: tileAppear 0.3s ease-out;
        }
        @keyframes tileAppear {
            from { opacity: 0; transform: scale(0.5); }
            to { opacity: 1; transform: scale(1); }
        }

        /* تنسيق متجاوب للعبة الدومينو بالطول على الهواتف */
        @media (max-width: 767px) {
            .domino-game-card {
                padding: 10px !important;
                width: 98vw !important;
                min-height: 85vh !important;
            }
            #domino-board {
                min-height: 250px !important;
                max-height: 380px !important;
                padding: 15px 5px !important;
                gap: 12px !important;
                overflow-y: auto !important;
                overflow-x: hidden !important;
            }
            .domino-tile {
                width: 32px !important;
                height: 64px !important;
            }
            #domino-board .domino-tile {
                width: 64px !important;
                height: 32px !important;
            }
            #domino-board .domino-tile.double {
                width: 32px !important;
                height: 64px !important;
            }
            .domino-tile.double {
                width: 32px !important;
                height: 64px !important;
            }
            .domino-half {
                font-size: 15px !important;
            }
            .domino-line::after {
                width: 4.5px !important;
                height: 4.5px !important;
            }
        }

        .domino-my-turn-active {
            animation: domino-turn-glow-pulse 1.8s infinite alternate !important;
            border-color: #00ffaa !important;
        }
        @keyframes domino-turn-glow-pulse {
            from { box-shadow: 0 0 12px rgba(0, 255, 170, 0.25), inset 0 0 6px rgba(0, 255, 170, 0.15); }
            to { box-shadow: 0 0 28px rgba(0, 255, 170, 0.7), inset 0 0 14px rgba(0, 255, 170, 0.45); }
        }

        /* Responsive styling for larger screen devices */
        @media (min-width: 600px) {
            .container { max-width: 100%; width: 100%; padding: 0; }
            .admin-wide-card { width: 100% !important; max-width: 100% !important; min-height: 100vh; padding: 40px !important; border-radius: 0 !important; margin: 0 !important; }
            .card { padding: 45px 35px; border-radius: 40px; }
            button { font-size: 22px; padding: 20px; border-radius: 22px; }
            input, select { font-size: 20px; padding: 20px; border-radius: 20px; }
            h1 { font-size: 42px; }
            h2 { font-size: 34px; }
            h3 { font-size: 28px; }
            .vote-item { font-size: 20px; padding: 22px; }
            .qa-chat-body { max-height: 350px; }
        }

        /* XO Styles */
        .xo-my-turn-active {
            animation: xo-turn-glow-pulse 1.8s infinite alternate;
            border-color: #00ff88 !important;
        }
        @keyframes xo-turn-glow-pulse {
            from { box-shadow: 0 0 12px rgba(0, 255, 136, 0.25), inset 0 0 6px rgba(0, 255, 136, 0.15); }
            to { box-shadow: 0 0 28px rgba(0, 255, 136, 0.7), inset 0 0 14px rgba(0, 255, 136, 0.45); }
        }

        .xo-board {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            max-width: 320px;
            margin: 20px auto;
            background: rgba(255, 255, 255, 0.03);
            padding: 12px;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        .xo-cell {
            aspect-ratio: 1;
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            font-weight: 900;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            user-select: none;
        }
        .xo-cell:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.2);
            transform: scale(1.05);
        }
        .xo-cell.x-symbol {
            color: #00d2ff;
            text-shadow: 0 0 15px rgba(0, 210, 255, 0.6);
        }
        .xo-cell.o-symbol {
            color: #ff2d55;
            text-shadow: 0 0 15px rgba(255, 45, 85, 0.6);
        }
        .xo-cell.disabled {
            cursor: not-allowed;
        }
        .xo-cell.playable-cell {
            animation: pulse-glow-xo 1.5s infinite alternate;
        }
        @keyframes pulse-glow-xo {
            from { border-color: rgba(0, 210, 255, 0.2); }
            to { border-color: rgba(0, 210, 255, 0.6); }
        }

        /* Uno CSS Styles */
        .uno-card-element {
            width: 75px;
            height: 110px;
            border-radius: 12px;
            display: inline-flex;
            justify-content: center;
            align-items: center;
            margin: 0 4px;
            font-weight: 900;
            font-size: 16px;
            color: white;
            position: relative;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            border: 2px solid rgba(255,255,255,0.25);
            user-select: none;
            flex-shrink: 0;
            touch-action: manipulation;
        }
        .uno-card-element:hover {
            transform: translateY(-8px);
        }
        .uno-card-inner {
            width: 86%;
            height: 86%;
            border: 2px dashed rgba(255,255,255,0.3);
            border-radius: 8px;
            display: flex;
            justify-content: center;
            align-items: center;
            background: rgba(0,0,0,0.15);
        }
        .uno-card-value {
            text-shadow: 2px 2px 4px rgba(0,0,0,0.6);
            font-size: 18px;
        }
        .uno-color-dot {
            width: 16px;
            height: 16px;
            border-radius: 50%;
            display: inline-block;
            margin-left: 6px;
            vertical-align: middle;
            border: 2.5px solid rgba(255,255,255,0.8);
            box-shadow: 0 0 6px rgba(0,0,0,0.6);
        }
        .uno-color-choice-btn {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            border: 3px solid rgba(255,255,255,0.4);
            cursor: pointer;
            transition: transform 0.1s;
        }
        .uno-color-choice-btn:hover {
            transform: scale(1.15);
            border-color: white;
        }
        .uno-neon-glow {
            animation: uno-neon 1.2s infinite alternate;
        }
        @keyframes uno-neon {
            from { box-shadow: 0 0 10px rgba(255, 118, 117, 0.4), inset 0 0 5px rgba(255, 118, 117, 0.2); }
            to { box-shadow: 0 0 25px rgba(255, 118, 117, 0.9), inset 0 0 10px rgba(255, 118, 117, 0.5); }
        }
    </style>
</head>
<body>
    <div class="menu-btn" onclick="toggleSidebar()">☰</div>
    <div class="exit-btn" id="global-exit-btn" onclick="confirmExitGame()">✖</div>

    <div id="sidebar-overlay" onclick="toggleSidebar()" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.3); z-index:999; backdrop-filter: blur(2px);"></div>

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
        <div id="sidebar-dynamic-top"></div>
        <button style="background:#25D366; color:white; font-size:14px;" onclick="window.open('https://wa.me/9647733921468', '_blank')">💬 تواصل مع مصمم اللعبة</button>
        <button style="background:var(--success); font-size:14px;" onclick="showReports()">📊 التقارير والمتصدرين</button>
        <button style="background:var(--primary); font-size:14px;" onclick="showEditProfile()">تعديل بيانات الحساب</button>
        <button id="share-game-btn" style="background:#0984e3; font-size:14px;" onclick="shareGame()">🔗 شارك اللعبة</button>
        <button id="install-btn-sidebar" style="background:var(--accent); color:black; font-size:14px;" onclick="showInstallOptions()">📲 إضافة للشاشة الرئيسية</button>
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
        let winLimit = 5;
        let isStartingGame = false; // قفل لمنع تداخل تحديث الواجهات
        let questionTimeout = 30;
        let voteTimeout = 10;
        let spyGuessTimeout = 15;
        let soundClickUrl = '';
        let soundRevealUrl = '';
        let soundWinUrl = '';
        let soundFailUrl = '';
        let appIconUrl = 'https://cdn-icons-png.flaticon.com/512/8030/8030198.png';
        let timerInterval = null;
        const CATEGORIES_DATA = {
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
        };
        const DEFAULT_CATEGORIES = Object.keys(CATEGORIES_DATA);

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
                if(d.app_icon_url) {
                    appIconUrl = d.app_icon_url;
                }
            } catch(e) { console.error("Settings fetch failed", e); }
        }

        function saveCachedCategories(cats) {
            localStorage.setItem('cachedCategories', JSON.stringify(cats));
        }

        function getCachedCategories() {
            const data = localStorage.getItem('cachedCategories');
            return data ? JSON.parse(data) : null;
        }

        async function prefetchCategories() {
            try {
                const res = await fetch('/api/categories');
                if (res.ok) {
                    const cats = await res.json();
                    saveCachedCategories(cats);
                }
            } catch(e) {}
        }

        function navigateTo(screen, data = {}, push = true) {
            lastRenderedHTML = "";
            if (push) {
                history.pushState({ screen, ...data }, "");
            }
            switch(screen) {
                case 'auth': showAuth(); break;
                case 'menu': showMenu(false); break;
                case 'game_selection': showGameSelection(); break;
                case 'bara_menu': showBaraMenu(); break;
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
                showGameSelection();
                history.replaceState({ screen: 'game_selection' }, "");
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
            const pending = localStorage.getItem('pendingJoin');
            const inviteNotice = pending ? `
                <div style="background: rgba(0, 255, 136, 0.1); border: 1px solid var(--accent); padding: 15px; border-radius: 15px; margin-bottom: 25px; animation: pulse 2s infinite;">
                    <p style="color: var(--accent); font-weight: bold; margin: 0;">🎮 وصلتك دعوة للعب!</p>
                    <p style="font-size: 13px; margin: 5px 0 0 0;">سجل دخولك أو أنشئ حساباً بسرعة للانضمام للغرفة</p>
                </div>` : '';

            document.getElementById('main-ui').innerHTML = `
                <div class="card" style="padding: 40px 20px;">
                    <div style="font-size: 60px; margin-bottom: 20px;">🕵️</div>
                    <h1 style="margin-bottom: 10px;">برا السالفة</h1>
                    <p style="color: #a29bfe; margin-bottom: 30px;">سجل دخولك لتلعب مع أصدقائك أونلاين</p>

                    ${inviteNotice}

                    <button onclick="showLogin()" style="margin-bottom: 15px; background: var(--primary);">تسجيل الدخول</button>
                    <button onclick="showRegister()" style="background: var(--accent); color: #000;">إنشاء حساب جديد</button>

                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1);">
                         <p style="font-size: 16px; color: #f1c40f;">✨ تصميم ابو الاكبر ✨</p>
                    </div>
                </div>`;
        }

        function showLogin() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>تسجيل الدخول</h2>
                    <input id="u_name" placeholder="يوزرك">
                    <input id="u_pass" type="password" placeholder="باسووردك">
                    <button onclick="login()" style="background: var(--primary); margin-top: 10px;">دخول ✅</button>
                    <button onclick="showAuth()" style="background: #636e72; margin-top: 10px;">رجوع</button>
                </div>`;
        }

        function showRegister() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>إنشاء حساب جديد</h2>
                    <input id="r_nick" placeholder="اسمك باللعبة">
                    <input id="u_name" placeholder="يوزرك">
                    <input id="u_pass" type="password" placeholder="باسووردك">
                    <button onclick="register()" style="background: var(--accent); color: #000; margin-top: 10px;">إنشاء الحساب 🚀</button>
                    <button onclick="showAuth()" style="background: #636e72; margin-top: 10px;">رجوع</button>
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

        function renderSnakeBoardHTML(board) {
            let html = "";
            // تحديد عدد الأحجار في الصف ديناميكياً: 3 للهواتف و 6 للشاشات الكبيرة
            let itemsPerRow = window.innerWidth < 600 ? 3 : 6; 
            let rows = [];
            
            // تقسيم الأحجار إلى صفوف تحتوي كل منها على itemsPerRow أحجار
            for (let i = 0; i < board.length; i += itemsPerRow) {
                rows.push(board.slice(i, i + itemsPerRow));
            }
            
            // رسم كل صف بشكل أفعواني متصل
            html = rows.map((rowTiles, rIdx) => {
                // الصفوف الزوجية (0، 2، 4) تتجه لليمين، والفردية (1، 3) تتجه لليسار بـ row-reverse
                let isReverse = rIdx % 2 !== 0;
                let flexDir = isReverse ? 'row-reverse' : 'row';
                
                let tilesHTML = rowTiles.map((tile, tIdx) => {
                    let isDouble = tile[0] === tile[1];
                    let tileClass = "domino-tile";
                    let extraStyle = "";
                    
                    if (isDouble) {
                        tileClass += " double";
                    }
                    
                    // التحقق من حجر الربط (آخر حجر في الصف إذا لم يكن الحجر الأخير في اللعبة كلها)
                    let isLastInRow = tIdx === rowTiles.length - 1;
                    let isLastInGame = (rIdx * itemsPerRow + tIdx) === board.length - 1;
                    
                    if (isLastInRow && !isLastInGame) {
                        // حجر ربط! يجب أن يقف ليربط بالصف السفلي
                        tileClass += " double"; // نجعله واقفاً (عرضه 44 وارتفاعه 84)
                        
                        // إضافة هوامش سلبية لربطه بالصف الذي يليه
                        extraStyle = "margin-top: 15px; margin-bottom: -15px; z-index: 2;";
                    }
                    
                    return `
                        <div class="${tileClass}" style="margin: 0 4px; ${extraStyle}">
                            <div class="domino-half">${tile[0]}</div>
                            <div class="domino-line"></div>
                            <div class="domino-half">${tile[1]}</div>
                        </div>
                    `;
                }).join('');
                
                return `
                    <div class="domino-board-row" style="display:flex; flex-direction:${flexDir}; align-items:center; justify-content:center; width:100%; min-height:90px; padding: 0 20px;">
                        ${tilesHTML}
                    </div>
                `;
            }).join('');
            
            return html;
        }

        function renderDominoGame() {
            if(!window.roomData) return;
            const {room, players} = window.roomData;
            const gd = room.game_data;
            const me = players.find(p => p.user_id == currentUser.user_id);
            const myHand = gd.hands[currentUser.user_id] || [];
            const isMyTurn = gd.ordered_ids[gd.turn_index] == currentUser.user_id;
            const board = gd.board || [];

            // التحقق من وجود هيكل اللعبة في الصفحة لتفادي الوميض
            let gameCard = document.querySelector('.domino-game-card');
            if (!gameCard) {
                // رسم الهيكل العام لأول مرة فقط
                let html = `
                    <div class="card domino-game-card" style="padding:15px; max-width:100%; width:98vw; min-height:80vh; display:flex; flex-direction:column;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                            <div>
                                <span id="domino-score-a" style="background:#3498db; padding:4px 10px; border-radius:10px; font-size:12px;">فريق A: ${gd.scores.A}</span>
                                <span id="domino-score-b" style="background:#e74c3c; padding:4px 10px; border-radius:10px; font-size:12px; margin-right:5px;">فريق B: ${gd.scores.B}</span>
                            </div>
                            <div id="domino-turn-info" style="color:var(--accent); font-weight:bold;"></div>
                            <button onclick="copyToClipboard('${room.room_code}')" style="background:rgba(255,255,255,0.1); padding:4px 10px; border-radius:10px; font-size:12px; border:1px solid #555; width:auto; margin:0;">📋 ${room.room_code}</button>
                        </div>

                        <!-- طاولة اللعب الأفعوانية القابلة للتمرير عمودياً -->
                        <div id="domino-board" style="direction:ltr; flex-grow:1; background:rgba(0,0,0,0.3); border-radius:20px; position:relative; overflow-y:auto; overflow-x:hidden; display:flex; flex-direction:column; align-items:center; justify-content:flex-start; padding:20px; border:2px dashed rgba(255,255,255,0.1); margin-bottom:20px; min-height:220px; gap:15px; width:100%; box-sizing:border-box;">
                        </div>

                        <!-- يد اللاعب -->
                        <div id="domino-player-hand-container" style="background:rgba(255,255,255,0.05); padding:15px; border-radius:20px;">
                        </div>
                    </div>`;
                document.getElementById('main-ui').innerHTML = html;
            }

            // تفعيل الإنارة المتوهجة والاهتزاز لتنبيه اللاعب عند بدء دوره
            const cardEl = document.querySelector('.domino-game-card');
            if (cardEl) {
                if (isMyTurn) {
                    cardEl.classList.add('domino-my-turn-active');
                    if (!window.wasMyDominoTurn) {
                        if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
                        window.wasMyDominoTurn = true;
                    }
                } else {
                    cardEl.classList.remove('domino-my-turn-active');
                    window.wasMyDominoTurn = false;
                }
            }

            // تحديث العناصر المتغيرة ديناميكياً بدون وميض
            const scoreAEl = document.getElementById('domino-score-a');
            const scoreBEl = document.getElementById('domino-score-b');
            if (scoreAEl) scoreAEl.innerText = `فريق A: ${gd.scores.A}`;
            if (scoreBEl) scoreBEl.innerText = `فريق B: ${gd.scores.B}`;

            const turnInfoEl = document.getElementById('domino-turn-info');
            if (turnInfoEl) {
                turnInfoEl.innerHTML = isMyTurn ? "🔴 دورك الآن!" : `دور: ${players.find(p=>p.user_id == gd.ordered_ids[gd.turn_index])?.player_name}`;
            }

            const boardEl = document.getElementById('domino-board');
            if (boardEl) {
                if (gd.phase === 'round_end') {
                    boardEl.innerHTML = `
                        <div style="text-align:center; width:100%; margin: auto 0;">
                            <h2 style="color:var(--accent)">انتهت الجولة!</h2>
                            <p>النقاط الحالية: A:${gd.scores.A} | B:${gd.scores.B}</p>
                            ${room.host_id == currentUser.user_id ?
                                `<button onclick="startNextDominoRound()" style="background:var(--success)">جولة جديدة 🔄</button>` :
                                `<p style="color:#aaa;">بانتظار المضيف لبدء الجولة التالية...</p>`
                            }
                        </div>
                    `;
                } else if (board.length === 0) {
                    boardEl.innerHTML = '<div style="color:#555; font-size:20px; width:100%; text-align:center; margin: auto 0;">الطاولة خالية.. ابدأ بوضع أول حجر</div>';
                } else {
                    boardEl.innerHTML = renderSnakeBoardHTML(board);
                }
            }

            const handContainerEl = document.getElementById('domino-player-hand-container');
            if (handContainerEl) {
                let handHTML = `
                    <div style="margin-bottom:10px; font-size:14px; display:flex; justify-content:space-between;">
                        <span>أحجارك (${myHand.length})</span>
                        <button onclick="drawDominoTile()" style="width:auto; padding:5px 15px; font-size:12px; background:var(--primary); display:${isMyTurn?'block':'none'}">➕ سحب حجر</button>
                    </div>
                    <div style="display:flex; flex-wrap:wrap; gap:10px; justify-content:center; padding:10px 0;">
                        ${myHand.map((tile, idx) => {
                            let isPlayable = false;
                            if (isMyTurn) {
                                if (board.length === 0) {
                                    isPlayable = true;
                                } else {
                                    const leftVal = board[0][0];
                                    const rightVal = board[board.length - 1][1];
                                    if (tile[0] === leftVal || tile[1] === leftVal || tile[0] === rightVal || tile[1] === rightVal) {
                                        isPlayable = true;
                                    }
                                }
                            }
                            return `
                            <div class="domino-tile ${isPlayable ? 'playable' : ''}" onclick="${isPlayable ? `selectDominoTile(${JSON.stringify(tile)})` : ''}" style="${!isPlayable && isMyTurn ? 'opacity:0.6; cursor:not-allowed;' : ''}">
                                <div class="domino-half">${tile[0]}</div>
                                <div class="domino-line"></div>
                                <div class="domino-half">${tile[1]}</div>
                            </div>
                            `;
                        }).join('')}
                    </div>
                `;
                handContainerEl.innerHTML = handHTML;
            }

            // تمرير تلقائي للأسفل لمتابعة أحدث حجر في الأفعى
            setTimeout(() => {
                const boardDiv = document.getElementById('domino-board');
                if (boardDiv) {
                    boardDiv.scrollTop = boardDiv.scrollHeight;
                }
            }, 100);
        }

        let selectedTile = null;
        function selectDominoTile(tile) {
            selectedTile = tile;
            const board = window.roomData.room.game_data.board;
            if (board.length === 0) {
                playDominoTile(tile, 'right');
                return;
            }

            const leftVal = board[0][0];
            const rightVal = board[board.length - 1][1];

            const canLeft = (tile[0] === leftVal || tile[1] === leftVal);
            const canRight = (tile[0] === rightVal || tile[1] === rightVal);

            if (canLeft && canRight && leftVal !== rightVal) {
                // يركب في الجهتين ومختلفتين، نسأل اللاعب
                const modal = document.createElement('div');
                modal.className = 'card';
                modal.style = "position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); z-index:10000; box-shadow:0 0 50px rgba(0,0,0,0.9);";
                modal.innerHTML = `
                    <h3>وين تبي تحط الحجر؟</h3>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px; margin-top:20px;">
                        <button onclick="playDominoTile(${JSON.stringify(tile)}, 'left'); this.parentElement.parentElement.remove()">➡️ اليسار</button>
                        <button onclick="playDominoTile(${JSON.stringify(tile)}, 'right'); this.parentElement.parentElement.remove()">اليمين ⬅️</button>
                    </div>
                    <button style="background:#636e72; margin-top:15px;" onclick="this.parentElement.remove()">إلغاء</button>
                `;
                document.body.appendChild(modal);
            } else if (canLeft) {
                playDominoTile(tile, 'left');
            } else if (canRight) {
                playDominoTile(tile, 'right');
            } else {
                showToast("هذا الحجر لا يركب!");
            }
        }

        async function playDominoTile(tile, side) {
            try {
                const res = await fetch('/api/domino/play', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({room_code: currentRoom, user_id: currentUser.user_id, tile, side})
                });
                const d = await res.json();
                if(!d.success) alert(d.msg);
            } catch(e) { console.error(e); }
        }

        async function drawDominoTile() {
            try {
                const res = await fetch('/api/domino/draw', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({room_code: currentRoom, user_id: currentUser.user_id})
                });
                const d = await res.json();
                if(!d.success) alert(d.msg);
                else {
                    if(d.msg) showToast(d.msg);
                    updateRoomState(); // تحديث الواجهة فوراً لرؤية الحجر الجديد
                }
            } catch(e) { console.error(e); }
        }

        async function startNextDominoRound() {
            try {
                const res = await fetch('/api/domino/next_round', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({room_code: currentRoom, user_id: currentUser.user_id})
                });
                const d = await res.json();
                if(!d.success) alert(d.msg);
            } catch(e) { console.error(e); }
        }

        function showGameSelection() {
            if(timerInterval) clearInterval(timerInterval);
            history.pushState({screen: 'game_selection'}, "");
            document.getElementById('main-ui').innerHTML = `
                <div class="card" style="padding: 30px 20px;">
                    <button id="announcement-bell" class="bell-btn" onclick="showAnnouncements()">
                        🔔
                        <div class="bell-badge"></div>
                    </button>
                    <div style="font-size: 60px; margin-bottom: 20px;">🎮</div>
                    <h1 style="margin-bottom: 10px;">اختر اللعبة</h1>
                    <p style="color: #a29bfe; margin-bottom: 30px; font-size: 16px;">ماذا تحب أن تلعب اليوم؟</p>

                    <button onclick="showBaraMenu()" style="margin-bottom: 15px; background: linear-gradient(135deg, #6c5ce7, #a29bfe);">🕵️‍♂️ برا السالفة</button>

                    <button onclick="showDominoMenu()" style="background: linear-gradient(135deg, #2d3436, #000); border: 1px solid #444;">🁔 دومينو (أونلاين)</button>

                    <button onclick="showXOMenu()" style="margin-top: 15px; background: linear-gradient(135deg, #00d2ff, #9d50bb); border: 1px solid #444;">❌⭕ اكس او (أونلاين)</button>

                    <button onclick="showUnoMenu()" style="margin-top: 15px; background: linear-gradient(135deg, #ff7675, #d63031); border: 1px solid #444;">🃏 أونو (أونلاين)</button>

                    <div style="margin-top: 25px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.08);">
                        <p style="font-size: 20px; color:#fff;">صُممت لكم بايدي ابو الاكبر   ❤️</p>
                    </div>
                </div>`;
            checkAnnouncements();
        }

        function showDominoMenu() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <button id="announcement-bell" class="bell-btn" onclick="showAnnouncements()">
                        🔔
                        <div class="bell-badge"></div>
                    </button>
                    <h1>🁔 دومينو أونلاين</h1>
                    <p style="color:#aaa; margin-bottom:20px;">العب مع أصدقائك بنظام الفرق (2 لاعبين أو 4)</p>

                    <button onclick="createDominoRoom()" style="background:var(--success); margin-bottom:15px;">✨ إنشاء طاولة جديدة</button>
                    <button onclick="showDominoJoinInput()" style="background:var(--primary); margin-bottom:15px;">🚪 انضمام لطاولة</button>

                    <button style="background:#636e72; margin-top:20px;" onclick="showGameSelection()">رجوع</button>
                </div>`;
            checkAnnouncements();
        }

        async function createDominoRoom() {
            if (!currentUser) return alert("سجل دخولك أولاً");
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>إعداد طاولة الدومينو</h2>
                    <p style="margin-bottom:20px;">اختر عدد اللاعبين المسموح به في الطاولة:</p>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px; margin-bottom:20px;">
                        <button onclick="submitCreateDomino(2)" style="background:var(--success); font-size:18px;">👥 2 لاعبين</button>
                        <button onclick="submitCreateDomino(4)" style="background:var(--primary); font-size:18px;">👨‍👩‍👧‍👦 4 لاعبين</button>
                    </div>
                    <button onclick="showDominoMenu()" style="background:#636e72;">إلغاء</button>
                </div>`;
        }

        async function submitCreateDomino(maxPlayers) {
            if (!currentUser) return alert("سجل دخولك أولاً");

            // إضافة شاشة التحميل بشكل يدوي إذا لم تكن موجودة برمجياً
            const mainUi = document.getElementById('main-ui');
            const originalContent = mainUi.innerHTML;
            mainUi.innerHTML = `
                <div class="card">
                    <div class="spinner" style="margin: 20px auto;"></div>
                    <h2 style="color:var(--accent)">جاري إنشاء الطاولة...</h2>
                    <p>لحظات ويجهز رمز اللعب 🚀</p>
                </div>`;

            try {
                const res = await fetch('/api/domino/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        user_id: currentUser.user_id,
                        player_name: currentUser.player_name,
                        max_players: maxPlayers
                    })
                });

                if (!res.ok) throw new Error("Server response not ok");
                const d = await res.json();

                if(d.success) {
                    currentRoom = d.room_code;
                    showDominoRoomInfo(d.room_code);
                } else {
                    mainUi.innerHTML = originalContent; // استعادة المحتوى السابق عند الفشل
                    alert(d.msg || "فشل إنشاء الغرفة");
                }
            } catch(e) {
                mainUi.innerHTML = originalContent;
                console.error('Fetch error:', e);
                alert("تعذر الاتصال بالخادم. يرجى المحاولة مرة أخرى.");
            }
        }

        function showDominoRoomInfo(code) {
            const joinLink = `${window.location.origin}/join/${code}`;
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2 style="color:var(--accent)">تم إنشاء الطاولة! ✨</h2>
                    <p style="margin-bottom:10px;">رمز الطاولة:</p>
                    <div style="font-size:40px; font-weight:900; background:rgba(255,255,255,0.05); padding:10px; border-radius:15px; margin-bottom:20px; letter-spacing:5px; border:2px dashed var(--accent);">${code}</div>

                    <p style="margin-bottom:10px;">أرسل هذا الرابط لأصدقائك:</p>
                    <div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:10px; font-size:12px; margin-bottom:15px; word-break:break-all;">${joinLink}</div>

                    <button onclick="copyToClipboard('${joinLink}')" style="background:var(--primary); margin-bottom:15px;">📋 نسخ رابط الدعوة</button>
                    <button onclick="startPolling()" style="background:var(--success);">دخول لغرفة الانتظار 🚪</button>
                </div>`;
        }

        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                showToast("تم نسخ الرابط! أرسله الآن لأصدقائك 🚀");
            });
        }

        function renderDominoLobby() {
            const {room, players} = window.roomData;
            const isHost = room.host_id == currentUser.user_id;
            const joinLink = `${window.location.origin}/join/${room.room_code}`;

            let playersHTML = players.map(p => `
                <div style="background:rgba(255,255,255,0.05); padding:10px; border-radius:10px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
                    <span>👤 ${p.player_name} ${p.user_id == room.host_id ? '👑' : ''}</span>
                    <span style="color:var(--success); font-size:12px;">متصل</span>
                </div>
            `).join('');

            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2 style="color:var(--accent)">غرفة انتظار الدومينو</h2>
                    <p style="font-size:14px; color:#aaa;">الرمز: <b style="color:white; font-size:18px;">${room.room_code}</b></p>

                    <div style="margin:20px 0; background:rgba(0,0,0,0.2); padding:15px; border-radius:15px; text-align:right;">
                        <h4 style="margin-top:0; border-bottom:1px solid #333; padding-bottom:5px;">اللاعبين (${players.length}/${room.max_players})</h4>
                        ${playersHTML}
                    </div>

                    ${isHost ? `
                        <button id="start-domino-btn" onclick="startDominoGame()" style="background:var(--success); margin-bottom:15px;" ${players.length < room.max_players ? 'disabled' : ''}>
                            ${players.length < room.max_players ? `بانتظار اكتمال العدد (${room.max_players})` : 'ابدأ اللعب الآن! 🚀'}
                        </button>
                    ` : `
                        <div style="background:rgba(241,196,15,0.1); color:#f1c40f; padding:10px; border-radius:10px; font-size:14px; margin-bottom:15px;">
                            ⏳ بانتظار المضيف لبدء اللعبة...
                        </div>
                    `}

                    <button onclick="copyToClipboard('${joinLink}')" style="background:rgba(255,255,255,0.1); font-size:14px; margin-bottom:10px;">📋 نسخ رابط الطاولة</button>
                    <button onclick="leaveRoom()" style="background:var(--error); font-size:14px;">خروج</button>
                </div>`;
        }

        async function startDominoGame() {
            try {
                const res = await fetch('/api/domino/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({room_code: currentRoom, user_id: currentUser.user_id})
                });
                const d = await res.json();
                if(!d.success) alert(d.msg);
            } catch(e) { console.error(e); }
        }

        function showDominoJoinInput() {
            console.log('Showing Domino Join Input');
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2 style="color:var(--accent)">انضمام لطاولة دومينو</h2>
                    <p style="margin-bottom:15px; color:#aaa;">أدخل رمز الطاولة المكون من 4 أحرف</p>
                    <input id="domino_join_code" placeholder="مثلاً: ABCD" style="text-transform:uppercase; text-align:center; font-size:24px; margin-bottom:20px; width:100%; letter-spacing:5px;">
                    <button id="domino-join-btn-final" onclick="joinDominoRoom()" style="background:var(--success); font-weight:bold;">انضمام الآن 🚪</button>
                    <button onclick="showDominoMenu()" style="background:#636e72; margin-top:10px;">رجوع</button>
                </div>`;

            // تركيز تلقائي على الحقل
            setTimeout(() => document.getElementById('domino_join_code').focus(), 100);
        }

        async function joinDominoRoom() {
            const btn = document.getElementById('domino-join-btn-final');
            const codeInput = document.getElementById('domino_join_code');
            const code = codeInput.value.trim().toUpperCase();

            if(!code) return alert("يرجى إدخال رمز الطاولة");
            if(!currentUser) return alert("سجل دخولك أولاً");

            console.log('Attempting to join Domino Room:', code);
            btn.disabled = true;
            btn.innerText = "جاري الانضمام...";

            try {
                const res = await fetch('/api/online/join', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        room_code: code,
                        user_id: currentUser.user_id,
                        player_name: currentUser.player_name
                    })
                });

                const d = await res.json();
                console.log('Join response:', d);

                if(d.success) {
                    currentRoom = code;
                    showToast("تم الانضمام بنجاح! 🚀");
                    startPolling();
                } else {
                    alert(d.msg || "تعذر الانضمام للغرفة");
                    btn.disabled = false;
                    btn.innerText = "انضمام الآن 🚪";
                }
            } catch(e) {
                console.error('Join Error:', e);
                alert("حدث خطأ أثناء الاتصال بالسيرفر");
                btn.disabled = false;
                btn.innerText = "انضمام الآن 🚪";
            }
        }

        /* XO Functions */
        function showXOMenu() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <button id="announcement-bell" class="bell-btn" onclick="showAnnouncements()">
                        🔔
                        <div class="bell-badge"></div>
                    </button>
                    <h1>❌⭕ لعبة اكس او</h1>
                    <p style="color:#aaa; margin-bottom:20px;">اختر طريقة اللعب المفضلة لديك:</p>

                    <button onclick="showXOOnlineMenu()" style="background:var(--success); margin-bottom:15px; font-weight:bold;">🌐 لعب أونلاين (مع صديق)</button>
                    <button onclick="startXOOfflineGame()" style="background:linear-gradient(135deg, #e056fd, #be2edd); margin-bottom:15px; font-weight:bold;">👥 لعب أوفلاين (مع شخص بجانبك)</button>

                    <button style="background:#636e72; margin-top:20px;" onclick="showGameSelection()">رجوع</button>
                </div>`;
            checkAnnouncements();
        }

        function showXOOnlineMenu() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <button id="announcement-bell" class="bell-btn" onclick="showAnnouncements()">
                        🔔
                        <div class="bell-badge"></div>
                    </button>
                    <h1>❌⭕ اكس او أونلاين</h1>
                    <p style="color:#aaa; margin-bottom:20px;">العب مع صديقك مواجهة ثنائية حماسية أونلاين!</p>

                    <button onclick="createXORoom()" style="background:var(--success); margin-bottom:15px;">✨ إنشاء غرفة جديدة</button>
                    <button onclick="showXOJoinInput()" style="background:var(--primary); margin-bottom:15px;">🚪 انضمام لغرفة</button>

                    <button style="background:#636e72; margin-top:20px;" onclick="showXOMenu()">رجوع</button>
                </div>`;
            checkAnnouncements();
        }

        /* XO Offline Mode Functions */
        let xoOfflineBoard = ["", "", "", "", "", "", "", "", ""];
        let xoOfflineTurn = "X";
        let xoOfflineScores = {X: 0, O: 0};
        let xoOfflinePhase = "playing";
        let xoOfflineWinner = null;

        function startXOOfflineGame() {
            xoOfflineBoard = ["", "", "", "", "", "", "", "", ""];
            xoOfflineTurn = "X";
            xoOfflinePhase = "playing";
            xoOfflineWinner = null;
            renderXOOfflineGame();
        }

        function renderXOOfflineGame() {
            let wrapper = document.getElementById('xo-game-wrapper');
            if (!wrapper) {
                document.getElementById('main-ui').innerHTML = `
                    <div id="xo-game-wrapper" class="card" style="padding:15px; max-width:100%; width:98vw; min-height:80vh; display:flex; flex-direction:column; justify-content: space-between;">
                        <div>
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; width: 100%;">
                                <div>
                                    <span id="xo-score-x-badge" style="background:#3498db; padding:4px 10px; border-radius:10px; font-size:12px;">نقاط X: <span id="xo-score-x">0</span></span>
                                    <span id="xo-score-o-badge" style="background:#e74c3c; padding:4px 10px; border-radius:10px; font-size:12px; margin-right:5px;">نقاط O: <span id="xo-score-o">0</span></span>
                                </div>
                                <div style="font-size: 14px; color:#aaa; font-weight:bold;">🎮 لعب أوفلاين (محلي)</div>
                            </div>
                            <div id="xo-turn-info" style="color:var(--accent); font-weight:bold; font-size: 18px; margin-bottom: 20px; text-align: center;"></div>
                            
                            <div class="xo-board">
                                <div id="xo-cell-0" class="xo-cell"></div>
                                <div id="xo-cell-1" class="xo-cell"></div>
                                <div id="xo-cell-2" class="xo-cell"></div>
                                <div id="xo-cell-3" class="xo-cell"></div>
                                <div id="xo-cell-4" class="xo-cell"></div>
                                <div id="xo-cell-5" class="xo-cell"></div>
                                <div id="xo-cell-6" class="xo-cell"></div>
                                <div id="xo-cell-7" class="xo-cell"></div>
                                <div id="xo-cell-8" class="xo-cell"></div>
                            </div>
                        </div>
                        <div>
                            <div id="xo-round-end-container"></div>
                            <button onclick="showXOMenu()" style="background:#636e72; margin-top:20px; font-size:14px; width:auto; padding:6px 20px; align-self:center;">خروج للقائمة</button>
                        </div>
                    </div>`;
            }

            const fakeGD = {
                scores: xoOfflineScores,
                phase: xoOfflinePhase
            };
            updateXOGameDOM(fakeGD, [], false);
            return;
            // Logic below bypassed
            let headerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; width: 100%;">
                    <div>
                        <span style="background:#3498db; padding:4px 10px; border-radius:10px; font-size:12px;">نقاط X: ${xoOfflineScores.X}</span>
                        <span style="background:#e74c3c; padding:4px 10px; border-radius:10px; font-size:12px; margin-right:5px;">نقاط O: ${xoOfflineScores.O}</span>
                    </div>
                    <div style="font-size: 14px; color:#aaa; font-weight:bold;">🎮 لعب أوفلاين (محلي)</div>
                </div>
            `;

            let turnInfoHTML = `
                <div style="color:var(--accent); font-weight:bold; font-size: 18px; margin-bottom: 20px; text-align: center;">
                    ${xoOfflinePhase === 'playing' ? `دور اللاعب: <span style="color:${xoOfflineTurn === 'X' ? '#00d2ff' : '#ff2d55'}">${xoOfflineTurn}</span>` : 'انتهت الجولة!'}
                </div>
            `;

            let boardHTML = `
                <div class="xo-board">
                    ${xoOfflineBoard.map((cell, idx) => {
                        let cellClass = "xo-cell";
                        if (cell === 'X') cellClass += " x-symbol";
                        if (cell === 'O') cellClass += " o-symbol";
                        
                        let clickAction = "";
                        if (cell === "" && xoOfflinePhase === 'playing') {
                            clickAction = `onclick="playXOOfflineMove(${idx})"`;
                            cellClass += " playable-cell";
                        } else {
                            cellClass += " disabled";
                        }

                        return `<div class="${cellClass}" ${clickAction}>${cell}</div>`;
                    }).join('')}
                </div>
            `;

            let roundEndHTML = "";
            if (xoOfflinePhase === 'ended') {
                let statusText = "";
                if (xoOfflineWinner === 'draw') {
                    statusText = "تعادل الجولة! 🤝";
                } else {
                    statusText = `الفائز في الجولة: ${xoOfflineWinner} 🎉`;
                }

                roundEndHTML = `
                    <div style="text-align:center; margin-top:20px; background:rgba(0,0,0,0.4); padding:15px; border-radius:20px; border:1px solid rgba(255,255,255,0.1);">
                        <h3 style="color:var(--accent); margin-top:0;">${statusText}</h3>
                        <button onclick="startXOOfflineGame()" style="background:var(--success); width:auto; padding:8px 25px;">جولة جديدة 🔄</button>
                    </div>
                `;
            }

            document.getElementById('main-ui').innerHTML = `
                <div class="card" style="padding:15px; max-width:100%; width:98vw; min-height:80vh; display:flex; flex-direction:column; justify-content: space-between;">
                    <div>
                        ${headerHTML}
                        ${turnInfoHTML}
                        ${boardHTML}
                    </div>
                    <div>
                        ${roundEndHTML}
                        <button onclick="showXOMenu()" style="background:#636e72; margin-top:20px; font-size:14px; width:auto; padding:6px 20px; align-self:center;">خروج للقائمة</button>
                    </div>
                </div>`;
        }

        function updateXOGameDOM(gd, players, isOnline) {
            // تفعيل الإنارة المتوهجة والاهتزاز لتنبيه اللاعبين عند بدء دورهم
            const wrapper = document.getElementById('xo-game-wrapper');
            if (wrapper) {
                if (gd.phase === 'playing') {
                    if (isOnline) {
                        const isMyTurn = gd.ordered_ids[gd.turn_index] == currentUser.user_id;
                        if (isMyTurn) {
                            wrapper.classList.add('xo-my-turn-active');
                            if (!window.wasMyXOTurn) {
                                if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
                                window.wasMyXOTurn = true;
                            }
                        } else {
                            wrapper.classList.remove('xo-my-turn-active');
                            window.wasMyXOTurn = false;
                        }
                    } else {
                        // وضع أوفلاين: تفعيل التوهج وتنبيه اللاعبين بالاهتزاز عند تبادل الأدوار
                        wrapper.classList.add('xo-my-turn-active');
                        if (window.wasMyXOOfflineTurn !== xoOfflineTurn) {
                            if (navigator.vibrate) navigator.vibrate(200);
                            window.wasMyXOOfflineTurn = xoOfflineTurn;
                        }
                    }
                } else {
                    wrapper.classList.remove('xo-my-turn-active');
                    window.wasMyXOTurn = false;
                    window.wasMyXOOfflineTurn = "";
                }
            }

            const scoreXEl = document.getElementById('xo-score-x');
            const scoreOEl = document.getElementById('xo-score-o');
            if (scoreXEl) scoreXEl.innerText = gd.scores.X;
            if (scoreOEl) scoreOEl.innerText = gd.scores.O;

            if (isOnline) {
                const mySymbolEl = document.getElementById('xo-my-symbol');
                if (mySymbolEl) {
                    const mySymbol = gd.symbols[currentUser.user_id] || "";
                    mySymbolEl.innerText = mySymbol;
                    mySymbolEl.style.color = mySymbol === 'X' ? '#00d2ff' : '#ff2d55';
                }
            }

            const turnInfoEl = document.getElementById('xo-turn-info');
            if (turnInfoEl) {
                if (gd.phase === 'playing') {
                    if (isOnline) {
                        const isMyTurn = gd.ordered_ids[gd.turn_index] == currentUser.user_id;
                        const currentTurnPlayer = players.find(p => p.user_id == gd.ordered_ids[gd.turn_index])?.player_name || "لاعب آخر";
                        turnInfoEl.innerHTML = isMyTurn ? "🔴 دورك الآن للعب!" : `انتظر دور: ${currentTurnPlayer}`;
                    } else {
                        turnInfoEl.innerHTML = `دور اللاعب: <span style="color:${xoOfflineTurn === 'X' ? '#00d2ff' : '#ff2d55'}">${xoOfflineTurn}</span>`;
                    }
                    turnInfoEl.style.display = 'block';
                } else {
                    turnInfoEl.style.display = 'none';
                }
            }

            const board = isOnline ? gd.board : xoOfflineBoard;
            const isMyTurn = isOnline ? (gd.ordered_ids[gd.turn_index] == currentUser.user_id) : true;
            const isPlaying = gd.phase === 'playing';

            for (let idx = 0; idx < 9; idx++) {
                const cellEl = document.getElementById(`xo-cell-${idx}`);
                if (cellEl) {
                    const val = board[idx];
                    cellEl.innerText = val;

                    let cellClass = "xo-cell";
                    if (val === 'X') cellClass += " x-symbol";
                    if (val === 'O') cellClass += " o-symbol";

                    if (val === "" && isMyTurn && isPlaying) {
                        cellClass += " playable-cell";
                        cellEl.className = cellClass;
                        cellEl.onclick = function() {
                            if (isOnline) playXOMove(idx);
                            else playXOOfflineMove(idx);
                        };
                    } else {
                        cellClass += " disabled";
                        cellEl.className = cellClass;
                        cellEl.onclick = null;
                    }
                }
            }

            const roundEndEl = document.getElementById('xo-round-end-container');
            if (roundEndEl) {
                if (gd.phase === 'ended') {
                    let statusText = "";
                    if (isOnline) {
                        if (gd.winner_id === 'draw') statusText = "تعادل الجولة! 🤝";
                        else {
                            const winnerName = players.find(p => p.user_id == gd.winner_id)?.player_name || "اللاعب";
                            statusText = `الفائز في الجولة: ${winnerName} 🎉`;
                        }
                    } else {
                        if (xoOfflineWinner === 'draw') statusText = "تعادل الجولة! 🤝";
                        else statusText = `الفائز في الجولة: ${xoOfflineWinner} 🎉`;
                    }

                    let btnHTML = "";
                    if (isOnline) {
                        const {room} = window.roomData;
                        const isHost = room.host_id == currentUser.user_id;
                        btnHTML = isHost ? `<button onclick="startNextXORound()" style="background:var(--success); width:auto; padding:8px 25px;">جولة جديدة 🔄</button>` : `<p style="color:#aaa;">بانتظار المضيف لبدء الجولة التالية...</p>`;
                    } else {
                        btnHTML = `<button onclick="startXOOfflineGame()" style="background:var(--success); width:auto; padding:8px 25px;">جولة جديدة 🔄</button>`;
                    }

                    roundEndEl.innerHTML = `
                        <div style="text-align:center; margin-top:20px; background:rgba(0,0,0,0.4); padding:15px; border-radius:20px; border:1px solid rgba(255,255,255,0.1);">
                            <h3 style="color:var(--accent); margin-top:0;">${statusText}</h3>
                            ${btnHTML}
                        </div>
                    `;
                    roundEndEl.style.display = 'block';
                } else {
                    roundEndEl.innerHTML = "";
                    roundEndEl.style.display = 'none';
                }
            }
        }

        function checkOfflineWin(board) {
            const winCombinations = [
                [0, 1, 2], [3, 4, 5], [6, 7, 8],
                [0, 3, 6], [1, 4, 7], [2, 5, 8],
                [0, 4, 8], [2, 4, 6]
            ];
            for (let combo of winCombinations) {
                if (board[combo[0]] !== "" && board[combo[0]] === board[combo[1]] && board[combo[0]] === board[combo[2]]) {
                    return board[combo[0]];
                }
            }
            return null;
        }

        function playXOOfflineMove(idx) {
            if (xoOfflineBoard[idx] !== "" || xoOfflinePhase !== 'playing') return;
            
            xoOfflineBoard[idx] = xoOfflineTurn;
            
            const winner = checkOfflineWin(xoOfflineBoard);
            if (winner) {
                xoOfflinePhase = "ended";
                xoOfflineWinner = winner;
                xoOfflineScores[winner] += 1;
            } else if (!xoOfflineBoard.includes("")) {
                xoOfflinePhase = "ended";
                xoOfflineWinner = "draw";
            } else {
                xoOfflineTurn = xoOfflineTurn === "X" ? "O" : "X";
            }
            
            renderXOOfflineGame();
        }


        async function createXORoom() {
            if (!currentUser) return alert("سجل دخولك أولاً");
            
            const mainUi = document.getElementById('main-ui');
            const originalContent = mainUi.innerHTML;
            mainUi.innerHTML = `
                <div class="card">
                    <div class="spinner" style="margin: 20px auto;"></div>
                    <h2 style="color:var(--accent)">جاري إنشاء الطاولة...</h2>
                    <p>لحظات ويجهز رمز اللعب 🚀</p>
                </div>`;

            try {
                const res = await fetch('/api/xo/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        user_id: currentUser.user_id,
                        player_name: currentUser.player_name
                    })
                });

                if (!res.ok) throw new Error("Server response not ok");
                const d = await res.json();

                if(d.success) {
                    currentRoom = d.room_code;
                    startPolling();
                } else {
                    mainUi.innerHTML = originalContent;
                    alert(d.msg || "فشل إنشاء الغرفة");
                }
            } catch(e) {
                console.error(e);
                mainUi.innerHTML = originalContent;
                alert("حدث خطأ أثناء الاتصال بالسيرفر");
            }
        }

        function showXOJoinInput() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2 style="color:var(--accent)">انضمام لطاولة اكس او</h2>
                    <p style="margin-bottom:15px; color:#aaa;">أدخل رمز الطاولة المكون من 4 أحرف</p>
                    <input id="xo_join_code" placeholder="مثلاً: ABCD" style="text-transform:uppercase; text-align:center; font-size:24px; margin-bottom:20px; width:100%; letter-spacing:5px;">
                    <button id="xo-join-btn-final" onclick="joinXORoom()" style="background:var(--success); font-weight:bold;">انضمام الآن 🚪</button>
                    <button onclick="showXOOnlineMenu()" style="background:#636e72; margin-top:10px;">رجوع</button>
                </div>`;

            setTimeout(() => {
                const el = document.getElementById('xo_join_code');
                if (el) el.focus();
            }, 100);
        }

        async function joinXORoom() {
            const btn = document.getElementById('xo-join-btn-final');
            const codeInput = document.getElementById('xo_join_code');
            const code = codeInput.value.trim().toUpperCase();

            if(!code) return alert("يرجى إدخال رمز الطاولة");
            if(!currentUser) return alert("سجل دخولك أولاً");

            btn.disabled = true;
            btn.innerText = "جاري الانضمام...";

            try {
                const res = await fetch('/api/online/join', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        room_code: code,
                        user_id: currentUser.user_id,
                        player_name: currentUser.player_name
                    })
                });

                const d = await res.json();
                if(d.success) {
                    currentRoom = code;
                    showToast("تم الانضمام بنجاح! 🚀");
                    startPolling();
                } else {
                    alert(d.msg || "تعذر الانضمام للغرفة");
                    btn.disabled = false;
                    btn.innerText = "انضمام الآن 🚪";
                }
            } catch(e) {
                console.error(e);
                alert("حدث خطأ أثناء الاتصال بالسيرفر");
                btn.disabled = false;
                btn.innerText = "انضمام الآن 🚪";
            }
        }

        function renderXOLobby() {
            const {room, players} = window.roomData;
            const isHost = room.host_id == currentUser.user_id;
            const joinLink = `${window.location.origin}/join/${room.room_code}`;

            let playersHTML = players.map(p => `
                <div style="background:rgba(255,255,255,0.05); padding:10px; border-radius:10px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
                    <span>👤 ${p.player_name} ${p.user_id == room.host_id ? '👑' : ''}</span>
                    <span style="color:var(--success); font-size:12px;">متصل</span>
                </div>
            `).join('');

            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2 style="color:var(--accent)">غرفة انتظار إكس أو</h2>
                    <p style="font-size:14px; color:#aaa;">الرمز: <b style="color:white; font-size:18px;">${room.room_code}</b></p>

                    <div style="margin:20px 0; background:rgba(0,0,0,0.2); padding:15px; border-radius:15px; text-align:right;">
                        <h4 style="margin-top:0; border-bottom:1px solid #333; padding-bottom:5px;">اللاعبين (${players.length}/2)</h4>
                        ${playersHTML}
                    </div>

                    ${isHost ? `
                        <button id="start-xo-btn" onclick="startXOGame()" style="background:var(--success); margin-bottom:15px;" ${players.length < 2 ? 'disabled' : ''}>
                            ${players.length < 2 ? 'بانتظار انضمام لاعب آخر... ⏳' : 'ابدأ اللعب الآن! 🚀'}
                        </button>
                    ` : `
                        <div style="background:rgba(241,196,15,0.1); color:#f1c40f; padding:10px; border-radius:10px; font-size:14px; margin-bottom:15px;">
                            ⏳ بانتظار المضيف لبدء اللعبة...
                        </div>
                    `}

                    <button onclick="copyToClipboard('${joinLink}')" style="background:rgba(255,255,255,0.1); font-size:14px; margin-bottom:10px;">📋 نسخ رابط الطاولة</button>
                    <button onclick="leaveRoom()" style="background:var(--error); font-size:14px;">خروج</button>
                </div>`;
        }

        async function startXOGame() {
            try {
                const res = await fetch('/api/xo/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({room_code: currentRoom, user_id: currentUser.user_id})
                });
                const d = await res.json();
                if(!d.success) alert(d.msg);
            } catch(e) { console.error(e); }
        }

        function renderXOGame() {
            if(!window.roomData) return;
            const {room, players} = window.roomData;
            const gd = room.game_data;

            let wrapper = document.getElementById('xo-game-wrapper');
            if (!wrapper) {
                document.getElementById('main-ui').innerHTML = `
                    <div id="xo-game-wrapper" class="card" style="padding:15px; max-width:100%; width:98vw; min-height:80vh; display:flex; flex-direction:column; justify-content: space-between;">
                        <div>
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; width: 100%;">
                                <div>
                                    <span id="xo-score-x-badge" style="background:#3498db; padding:4px 10px; border-radius:10px; font-size:12px;">نقاط X: <span id="xo-score-x">0</span></span>
                                    <span id="xo-score-o-badge" style="background:#e74c3c; padding:4px 10px; border-radius:10px; font-size:12px; margin-right:5px;">نقاط O: <span id="xo-score-o">0</span></span>
                                </div>
                                <div style="font-size: 14px; color:#aaa;">رمزك: <span id="xo-my-symbol" style="font-weight:bold;"></span></div>
                                <button onclick="copyToClipboard('${room.room_code}')" style="background:rgba(255,255,255,0.1); padding:4px 10px; border-radius:10px; font-size:12px; border:1px solid #555; width:auto; margin:0;">📋 ${room.room_code}</button>
                            </div>
                            <div id="xo-turn-info" style="color:var(--accent); font-weight:bold; font-size: 18px; margin-bottom: 20px; text-align: center;"></div>
                            
                            <div class="xo-board">
                                <div id="xo-cell-0" class="xo-cell"></div>
                                <div id="xo-cell-1" class="xo-cell"></div>
                                <div id="xo-cell-2" class="xo-cell"></div>
                                <div id="xo-cell-3" class="xo-cell"></div>
                                <div id="xo-cell-4" class="xo-cell"></div>
                                <div id="xo-cell-5" class="xo-cell"></div>
                                <div id="xo-cell-6" class="xo-cell"></div>
                                <div id="xo-cell-7" class="xo-cell"></div>
                                <div id="xo-cell-8" class="xo-cell"></div>
                            </div>
                        </div>
                        <div>
                            <div id="xo-round-end-container"></div>
                            <button onclick="leaveRoom()" style="background:var(--error); margin-top:20px; font-size:14px; width:auto; padding:6px 20px; align-self:center;">انسحاب وخروج</button>
                        </div>
                    </div>`;
            }

            updateXOGameDOM(gd, players, true);
            return;
            // Logic below bypassed

            let headerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; width: 100%;">
                    <div>
                        <span style="background:#3498db; padding:4px 10px; border-radius:10px; font-size:12px;">نقاط X: ${gd.scores.X}</span>
                        <span style="background:#e74c3c; padding:4px 10px; border-radius:10px; font-size:12px; margin-right:5px;">نقاط O: ${gd.scores.O}</span>
                    </div>
                    <div style="font-size: 14px; color:#aaa;">رمزك: <span style="font-weight:bold; color:${mySymbol === 'X' ? '#00d2ff' : '#ff2d55'}">${mySymbol}</span></div>
                    <button onclick="copyToClipboard('${room.room_code}')" style="background:rgba(255,255,255,0.1); padding:4px 10px; border-radius:10px; font-size:12px; border:1px solid #555; width:auto; margin:0;">📋 ${room.room_code}</button>
                </div>
            `;

            let turnInfoHTML = `
                <div style="color:var(--accent); font-weight:bold; font-size: 18px; margin-bottom: 20px; text-align: center;">
                    ${isMyTurn ? "🔴 دورك الآن للعب!" : `انتظر دور: ${currentTurnPlayer}`}
                </div>
            `;

            let boardHTML = `
                <div class="xo-board">
                    ${board.map((cell, idx) => {
                        let cellClass = "xo-cell";
                        if (cell === 'X') cellClass += " x-symbol";
                        if (cell === 'O') cellClass += " o-symbol";
                        
                        let clickAction = "";
                        if (cell === "" && isMyTurn && gd.phase === 'playing') {
                            clickAction = `onclick="playXOMove(${idx})"`;
                            cellClass += " playable-cell";
                        } else {
                            cellClass += " disabled";
                        }

                        return `<div class="${cellClass}" ${clickAction}>${cell}</div>`;
                    }).join('')}
                </div>
            `;

            let roundEndHTML = "";
            if (gd.phase === 'ended') {
                let statusText = "";
                if (gd.winner_id === 'draw') {
                    statusText = "تعادل الجولة! 🤝";
                } else {
                    const winnerName = players.find(p => p.user_id == gd.winner_id)?.player_name || "اللاعب";
                    statusText = `الفائز في الجولة: ${winnerName} 🎉`;
                }

                roundEndHTML = `
                    <div style="text-align:center; margin-top:20px; background:rgba(0,0,0,0.4); padding:15px; border-radius:20px; border:1px solid rgba(255,255,255,0.1);">
                        <h3 style="color:var(--accent); margin-top:0;">${statusText}</h3>
                        ${room.host_id == currentUser.user_id ?
                            `<button onclick="startNextXORound()" style="background:var(--success); width:auto; padding:8px 25px;">جولة جديدة 🔄</button>` :
                            `<p style="color:#aaa;">بانتظار المضيف لبدء الجولة التالية...</p>`
                        }
                    </div>
                `;
            }

            document.getElementById('main-ui').innerHTML = `
                <div class="card" style="padding:15px; max-width:100%; width:98vw; min-height:80vh; display:flex; flex-direction:column; justify-content: space-between;">
                    <div>
                        ${headerHTML}
                        ${gd.phase === 'playing' ? turnInfoHTML : ''}
                        ${boardHTML}
                    </div>
                    <div>
                        ${roundEndHTML}
                        <button onclick="leaveRoom()" style="background:var(--error); margin-top:20px; font-size:14px; width:auto; padding:6px 20px; align-self:center;">انسحاب وخروج</button>
                    </div>
                </div>`;
        }

        async function playXOMove(idx) {
            try {
                const res = await fetch('/api/xo/play', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({room_code: currentRoom, user_id: currentUser.user_id, index: idx})
                });
                const d = await res.json();
                if(!d.success) alert(d.msg);
                else {
                    await updateRoomState();
                }
            } catch(e) { console.error(e); }
        }

        async function startNextXORound() {
            try {
                const res = await fetch('/api/xo/next_round', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({room_code: currentRoom, user_id: currentUser.user_id})
                });
                const d = await res.json();
                if(!d.success) alert(d.msg);
                else {
                    await updateRoomState();
                }
            } catch(e) { console.error(e); }
        }

        function showMenu(push = true) {
            if(timerInterval) clearInterval(timerInterval);
            if(push) history.pushState({screen: 'menu'}, "");
            if(document.getElementById('global-exit-btn')) document.getElementById('global-exit-btn').style.display = 'none';
            game = null;
            isStartingGame = false;
            winLimit = 5;
            window.pNamesSave = [];
            totalScores = {};

            showGameSelection();
        }

        function showGameSelection() {
            if(timerInterval) clearInterval(timerInterval);
            history.pushState({screen: 'game_selection'}, "");
            document.getElementById('main-ui').innerHTML = `
                <div class="card" style="padding: 30px 20px;">
                    <button id="announcement-bell" class="bell-btn" onclick="showAnnouncements()">
                        🔔
                        <div class="bell-badge"></div>
                    </button>
                    <div style="font-size: 60px; margin-bottom: 20px;">🎮</div>
                    <h1 style="margin-bottom: 10px;">اختر اللعبة</h1>
                    <p style="color: #a29bfe; margin-bottom: 30px; font-size: 16px;">ماذا تحب أن تلعب اليوم؟</p>

                    <button onclick="showBaraMenu()" style="margin-bottom: 15px; background: linear-gradient(135deg, #6c5ce7, #a29bfe);">🕵️‍♂️ برا السالفة</button>

                    <button onclick="showDominoMenu()" style="background: linear-gradient(135deg, #2d3436, #000); border: 1px solid #444;">🁔 دومينو (أونلاين)</button>

                    <button onclick="showXOMenu()" style="margin-top: 15px; background: linear-gradient(135deg, #00d2ff, #9d50bb); border: 1px solid #444;">❌⭕ اكس او (أونلاين)</button>

                    <button onclick="showUnoMenu()" style="margin-top: 15px; background: linear-gradient(135deg, #ff7675, #d63031); border: 1px solid #444;">🃏 أونو (أونلاين)</button>

                    <div style="margin-top: 25px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.08);">
                        <p style="font-size: 20px; color:#fff;">صُممت لكم بايدي ابو الاكبر   ❤️</p>
                    </div>
                </div>`;
            checkAnnouncements();
        }

        function showBaraMenu() {
            history.pushState({screen: 'bara_menu'}, "");
            document.getElementById('main-ui').innerHTML = `
                <div class="card" style="padding: 30px 20px;">
                    <button id="announcement-bell" class="bell-btn" onclick="showAnnouncements()">
                        🔔
                        <div class="bell-badge"></div>
                    </button>
                    <div style="font-size: 60px; margin-bottom: 20px;">🕵️‍♂️</div>
                    <h1 style="margin-bottom: 10px;">لعبة برا السالفة</h1>
                    <p style="color: #a29bfe; margin-bottom: 30px; font-size: 16px;">اكتشف الجاسوس قبل فوات الأوان!</p>
                    <button onclick="navigateTo('online_menu')" style="margin-bottom: 15px;">🌐 لعب أونلاين</button>
                    <button style="background: linear-gradient(45deg, #e056fd, #be2edd); margin-bottom: 15px;" onclick="navigateTo('setup', {step: 1})">🏠 لعب أوفلاين (مجلس)</button>

                    <button style="background:#636e72; margin-top:20px;" onclick="showGameSelection()">رجوع</button>

                    <div style="margin-top: 25px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.08);">
                        <p style="font-size: 20px; font-weight: 900; background: linear-gradient(to right, #f1c40f, #f39c12); -webkit-background-clip: text; -webkit-text-fill-color: transparent; drop-shadow: 0 2px 4px rgba(0,0,0,0.3); margin: 0; letter-spacing: 1px;">✨ تصميم ابو الاكبر ✨</p>
                    </div>
                </div>`;
            checkAnnouncements();
        }

        async function checkAnnouncements() {
            try {
                const res = await fetch('/api/announcements');
                const data = await res.json();
                if (data && data.length > 0) {
                    const latestId = data[0].id;
                    const lastSeenId = localStorage.getItem('last_seen_announcement') || 0;
                    if (latestId > lastSeenId) {
                        document.getElementById('announcement-bell').classList.add('dance');
                    }
                }
            } catch (e) { console.error("Error checking announcements:", e); }
        }

        async function showAnnouncements() {
            showLoading("جاري تحميل التحديثات...");
            try {
                const res = await fetch('/api/announcements');
                const data = await res.json();

                let html = `
                    <div class="card" style="max-height: 90vh; overflow-y: auto; width: 95%; max-width: 600px;">
                        <h2 style="color:var(--accent); margin-bottom:20px;">📢 آخر التحديثات والأخبار</h2>
                        <div id="announcements-list">`;

                if (!data || data.length === 0) {
                    html += `<p style="color:#9aa0b4; margin:40px 0;">لا توجد تحديثات حالياً.</p>`;
                } else {
                    data.forEach(ann => {
                        const date = new Date(ann.created_at).toLocaleString('ar-EG');
                        html += `
                            <div class="announcement-item" style="margin-bottom: 25px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 20px;">
                                <div style="font-size:16px; color:white; line-height:1.5;">${ann.text}</div>
                                <div class="announcement-date">${date}</div>

                                <div style="display:flex; gap:10px; margin-top:15px;">
                                    <button onclick="openFeedbackForm(${ann.id}, 'comment')" style="padding:5px 10px; font-size:12px; background:rgba(255,255,255,0.1); width:auto;">💬 تعليق</button>
                                    <button onclick="openFeedbackForm(${ann.id}, 'suggestion')" style="padding:5px 10px; font-size:12px; background:rgba(241, 196, 15, 0.2); color:#f1c40f; width:auto;">💡 اقتراح</button>
                                </div>

                                <div id="feedback-form-${ann.id}" style="display:none; margin-top:15px; background:rgba(0,0,0,0.2); padding:10px; border-radius:10px;">
                                    <textarea id="feedback-input-${ann.id}" style="width:100%; height:60px; background:#111; color:white; border:1px solid #444; border-radius:8px; padding:8px; font-size:14px;"></textarea>
                                    <div style="display:flex; justify-content:flex-end; gap:5px; margin-top:5px;">
                                        <button onclick="submitFeedback(${ann.id})" id="fb-submit-btn-${ann.id}" style="width:auto; padding:5px 15px; font-size:12px;">إرسال</button>
                                        <button onclick="this.parentElement.parentElement.style.display='none'" style="width:auto; padding:5px 15px; font-size:12px; background:#636e72;">إلغاء</button>
                                    </div>
                                </div>

                                <div class="feedback-section" style="margin-top:15px; padding-right:15px; border-right:2px solid rgba(255,255,255,0.05);">
                                    ${(ann.feedback || []).map(fb => {
                                        const isMyFb = currentUser && fb.user_id == currentUser.user_id;
                                        const isSuggestion = fb.type === 'suggestion';
                                        return `
                                            <div class="fb-item" style="margin-bottom:10px; font-size:13px; background:rgba(255,255,255,0.03); padding:8px; border-radius:8px;">
                                                <div style="display:flex; justify-content:space-between;">
                                                    <b style="color:var(--accent)">${fb.player_name}:</b>
                                                    <span style="font-size:10px; color:#777;">${isSuggestion ? '💡 اقتراح' : '💬 تعليق'}</span>
                                                </div>
                                                <div id="fb-text-${fb.id}" style="margin-top:5px; color:#ddd; text-align:right;">
                                                    ${fb.original_text ? `<div style="color:#777; font-size:11px; text-decoration:line-through; margin-bottom:2px;">(قبل التعديل: ${fb.original_text})</div>` : ''}
                                                    ${fb.original_text ? `<div style="color:var(--accent); font-size:11px; margin-bottom:2px;">(بعد التعديل):</div>` : ''}
                                                    ${fb.text}
                                                </div>
                                                ${isMyFb ? `
                                                    <div style="display:flex; gap:10px; margin-top:5px;">
                                                        <a href="javascript:void(0)" onclick="editFeedback(${fb.id}, '${fb.text.replace(/'/g, "\\'")}', '${fb.type}')" style="color:#3498db; font-size:11px;">تعديل</a>
                                                        ${!isSuggestion ? `<a href="javascript:void(0)" onclick="deleteFeedback(${fb.id})" style="color:#e74c3c; font-size:11px;">حذف</a>` : ''}
                                                    </div>
                                                ` : ''}
                                            </div>
                                        `;
                                    }).join('')}
                                </div>
                            </div>`;
                    });
                    localStorage.setItem('last_seen_announcement', data[0].id);
                }

                html += `
                        </div>
                        <button style="margin-top:20px;" onclick="navigateTo('menu')">إغلاق</button>
                    </div>`;

                document.getElementById('main-ui').innerHTML = html;
                document.getElementById('announcement-bell')?.classList.remove('dance');
            } catch (e) {
                console.error(e);
                alert("فشل تحميل التحديثات");
                navigateTo('menu');
            }
        }

        function openFeedbackForm(annId, type) {
            const form = document.getElementById(`feedback-form-${annId}`);
            const input = document.getElementById(`feedback-input-${annId}`);
            const btn = document.getElementById(`fb-submit-btn-${annId}`);
            form.style.display = 'block';
            input.placeholder = type === 'comment' ? "اكتب تعليقك هنا..." : "اكتب اقتراحك هنا...";
            btn.onclick = () => submitFeedback(annId, type);
            input.focus();
        }

        async function submitFeedback(annId, type) {
            const text = document.getElementById(`feedback-input-${annId}`).value.trim();
            if(!text) return;
            if(!currentUser) return alert("يرجى تسجيل الدخول أولاً");

            try {
                const res = await fetch('/api/feedback/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        announcement_id: annId,
                        user_id: currentUser.user_id,
                        player_name: currentUser.player_name,
                        text: text,
                        type: type
                    })
                });
                const d = await res.json();
                if(d.success) showAnnouncements();
            } catch(e) { console.error(e); }
        }

        async function editFeedback(id, oldText, type) {
            const newText = prompt("تعديل النص:", oldText);
            if(newText === null || newText.trim() === "" || newText === oldText) return;

            try {
                const res = await fetch('/api/feedback/update', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ id, text: newText.trim() })
                });
                const d = await res.json();
                if(d.success) showAnnouncements();
            } catch(e) { console.error(e); }
        }

        async function deleteFeedback(id) {
            if(!confirm("هل أنت متأكد من حذف التعليق؟")) return;
            try {
                const res = await fetch('/api/feedback/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ id })
                });
                const d = await res.json();
                if(d.success) showAnnouncements();
            } catch(e) { console.error(e); }
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

        let createData = { win_limit: 10, category: 'أكلات' };

        function showOnlineMenu(push = true) {
            if(push) history.pushState({screen: 'online_menu'}, "");
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h1>اللعب أونلاين</h1>
                    <button style="background: linear-gradient(135deg, #2ecc71, #27ae60); box-shadow: 0 4px 15px rgba(46, 204, 113, 0.4); border-radius: 20px; font-weight: 900; margin-bottom: 20px;" onclick="showCreateStep1()">✨ إنشاء غرفة جديدة</button>
                    <button style="background: var(--primary); margin-bottom: 20px;" onclick="showJoinInput()">🚪 انضمام لغرفة</button>

                    <button style="background:#636e72; margin-top:20px;" onclick="navigateTo('menu')">رجوع</button>
                </div>`;
        }

        function showJoinInput() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>انضمام لغرفة</h2>
                    <p style="color:#aaa; margin-bottom:20px;">أدخل رمز الغرفة المكون من 4 أحرف</p>
                    <input id="join_code" placeholder="رمز الغرفة (مثال: ABCD)" style="text-transform:uppercase; text-align:center; font-size:24px; letter-spacing:4px; margin-bottom:20px;">
                    <button onclick="joinRoom()" style="background:var(--success);">دخول الآن 🚪</button>
                    <button onclick="showOnlineMenu(false)" style="background:#636e72; margin-top:10px;">رجوع</button>
                </div>`;
        }

        function showCreateStep1() {
            createData.win_limit = 5; // الافتراضي 5 كما طلب المستخدم
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h1>إنشاء غرفة</h1>
                    <h3 style="margin-bottom:20px; color:var(--accent);">حدد نقاط الفوز:</h3>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-bottom:25px;">
                        ${[5, 10, 15, 20].map(v => `
                            <div class="win-opt ${createData.win_limit == v ? 'selected' : ''}"
                                 onclick="createData.win_limit=${v}; document.querySelectorAll('.win-opt').forEach(el=>el.classList.remove('selected')); this.classList.add('selected');">
                                ${v}
                            </div>
                        `).join('')}
                    </div>
                    <button onclick="showCreateStep2()" style="background:var(--success);">التالي: اختيار الفئة</button>
                    <button style="background:#636e72; margin-top:10px;" onclick="showOnlineMenu(false)">رجوع</button>
                </div>`;
        }

        async function showCreateStep2() {
            const cachedCats = getCachedCategories();
            let cats = (cachedCats && cachedCats.length) ? cachedCats : DEFAULT_CATEGORIES.map(name => ({ name }));

            let h = `
                <div class="card" style="max-width:95%;">
                    <h1>إنشاء غرفة</h1>
                    <h3 style="margin-bottom:10px; color:var(--accent);">اختر الفئة:</h3>
                    <div class="cat-grid" id="create-cat-grid">`;

            cats.forEach(cat => {
                h += `
                    <div class="cat-card" onclick="createData.category='${cat.name}'; createRoom()">
                        <div class="cat-image-wrapper">
                            <div class="image-placeholder">⏳</div>
                            <img data-src="${cat.image || ''}" alt="${cat.name}" onload="this.style.opacity=1; this.previousElementSibling.style.display='none';">
                        </div>
                        <span>${cat.name}</span>
                    </div>`;
            });

            h += `</div>
                    <button style="background:#636e72" onclick="showCreateStep1()">رجوع للخلف</button>
                </div>`;

            document.getElementById('main-ui').innerHTML = h;

            setTimeout(() => {
                const imgs = document.querySelectorAll('#create-cat-grid img');
                imgs.forEach(img => {
                    if (img.dataset.src) img.src = img.dataset.src;
                    else {
                        img.style.display = 'none';
                        img.previousElementSibling.innerText = '❓';
                    }
                });
            }, 50);

            if (!cachedCats || !cachedCats.length) {
                try {
                    const res = await fetch('/api/categories');
                    if (res.ok) {
                        const newCats = await res.json();
                        saveCachedCategories(newCats);
                    }
                } catch(e){}
            }
        }

        let isCreatingRoom = false;
        async function createRoom() {
            console.log('createRoom called', { currentUser });
            if (isCreatingRoom) return;
            if (!currentUser || !currentUser.user_id) {
                showError("بيانات المستخدم غير مكتملة. يرجى تسجيل الخروج والدخول مرة أخرى.", "خطأ في بيانات الحساب");
                return;
            }

            // عرض حالة تحميل بصرية جميلة فوراً حتى يعلم اللاعب ببدء العملية
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>جاري إنشاء الغرفة...</h2>
                    <p>يرجى الانتظار، نقوم بإعداد جلسة اللعب وسيرفر الغرفة حالياً.</p>
                    <div class="loading-spinner" style="margin: 20px auto;"></div>
                </div>`;

            isCreatingRoom = true;
            const category = createData.category;
            const winLimit = createData.win_limit;

            try {
                const res = await fetch('/api/online/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        user_id: currentUser.user_id.toString(), // إرسال كـ string لضمان الدقة
                        player_name: currentUser.player_name || "لاعب مجهول",
                        category: category,
                        win_limit: winLimit
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

        let lastStateHash = "";
        let activeStatePromise = null;
        async function updateRoomState() {
            if(!currentRoom) return false;
            if (activeStatePromise) return activeStatePromise;

            activeStatePromise = (async () => {
                try {
                    const res = await fetch(`/api/online/room/${currentRoom}`);
                    if (!res.ok) {
                        if (res.status === 404) {
                            showError("تم إغلاق الغرفة من قبل المضيف أو انتهت جلسة اللعب.", "الغرفة غير موجودة أو مغلقة");
                            leaveRoom();
                            return false;
                        }
                        throw new Error("Room fetch failed");
                    }
                    const d = await res.json();
                    if(d.success) {
                        // التحقق من تغير البيانات لمنع الوميض (الرمش)
                        const myHand = d.room.game_data?.hands?.[currentUser?.user_id] || [];
                        const currentStateHash = JSON.stringify({
                            status: d.room.status,
                            p_count: d.players.length,
                            turn: d.room.game_data?.turn_index,
                            board_len: d.room.game_data?.board?.length,
                            scores: d.room.game_data?.scores,
                            phase: d.room.game_data?.phase,
                            hand_hash: myHand.map(t => t.join('-')).join(',')
                        });

                        if (currentStateHash === lastStateHash) {
                            return true; // لم يتغير شيء، لا داعي للتحديث
                        }
                        lastStateHash = currentStateHash;

                        window.roomData = d;
                        const status = d.room.status;

                        // Ensure exit button is visible to ALL players since they are in an active room!
                        if(document.getElementById('global-exit-btn')) {
                            document.getElementById('global-exit-btn').style.display = 'block';
                        }

                        // التحديث البصري للحالة
                        if(status === 'waiting' || (['domino', 'xo', 'uno'].includes(d.room.game_type) && status === 'lobby')) {
                            renderRoom();
                        } else if(status === 'playing' && d.room.game_type === 'domino') {
                            renderDominoGame();
                        } else if(status === 'playing' && d.room.game_type === 'xo') {
                            renderXOGame();
                        } else if((status === 'playing' || status === 'finished') && d.room.game_type === 'uno') {
                            renderUnoGame();
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
                // Check if we need to update to avoid visual flickering/re-pulsing
                const currentTimer = document.getElementById('voting-limit-timer');
                if (currentTimer) currentTimer.innerText = `⏱️ الوقت المتبقي: ${timeLeft} ثانية`;

                const buttons = limitCard.querySelectorAll('.win-opt');
                buttons.forEach(btn => {
                    const val = parseInt(btn.getAttribute('data-value'));
                    const isSelected = myVote == val;
                    if (isSelected) {
                        if(!btn.classList.contains('selected')) btn.classList.add('selected');
                    } else {
                        btn.classList.remove('selected');
                    }
                });
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
                const currentTimer = document.getElementById('voting-cat-timer');
                if (currentTimer) currentTimer.innerText = `⏱️ الوقت المتبقي: ${timeLeft} ثانية`;

                const items = catCard.querySelectorAll('.vote-item');
                items.forEach(btn => {
                    const cat = btn.getAttribute('data-value');
                    const isSelected = myVote == cat;
                    if (isSelected) {
                        btn.style.background = 'var(--success)';
                        if (!btn.innerHTML.includes('✅')) btn.innerHTML = `${cat} ✅`;
                    } else {
                        btn.style.background = '';
                        btn.innerHTML = cat;
                    }
                });
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
            if(window.roomData.room.game_type === 'domino' && window.roomData.room.status === 'lobby') {
                return renderDominoLobby();
            }
            if(window.roomData.room.game_type === 'xo' && window.roomData.room.status === 'lobby') {
                return renderXOLobby();
            }
            if(window.roomData.room.game_type === 'uno' && window.roomData.room.status === 'lobby') {
                return renderUnoLobby();
            }
            const {room, players} = window.roomData;
            const me = players.find(p => p.user_id == currentUser.user_id);

            // المرحلة الأولى: اختيار نقاط الفوز (للانضمام)
            if (!me.vote_limit) {
                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2 style="color:var(--accent)">تصويت: نقاط الفوز 🎯</h2>
                        <p style="margin-bottom:20px;">أهلاً بك في الغرفة ${room.room_code}. اختر عدد النقاط الذي تفضله للفوز:</p>
                        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:10px; margin-bottom:25px;">
                            ${[5, 10, 15, 20, 30, 50].map(v => `
                                <div class="win-opt" onclick="submitLobbyVote('limit', ${v})">
                                    ${v}
                                </div>
                            `).join('')}
                        </div>
                        <button style="background:#636e72" onclick="leaveRoom()">خروج من الغرفة</button>
                    </div>`;
                return;
            }

            // المرحلة الثانية: اختيار الفئة (للانضمام)
            if (!me.vote_cat) {
                const cachedCats = getCachedCategories();
                let cats = (cachedCats && cachedCats.length) ? cachedCats : DEFAULT_CATEGORIES.map(name => ({ name }));

                let h = `
                    <div class="card" style="max-width:95%;">
                        <h2 style="color:var(--accent)">تصويت: الفئة 📂</h2>
                        <p style="margin-bottom:10px;">اختر الفئة التي تريد اللعب بها:</p>
                        <div class="cat-grid" id="vote-cat-grid">`;

                cats.forEach(cat => {
                    h += `
                        <div class="cat-card" onclick="submitLobbyVote('cat', '${cat.name}')">
                            <div class="cat-image-wrapper">
                                <div class="image-placeholder">🖼️</div>
                                <img src="${cat.image || ''}" onload="this.style.opacity=1; this.previousElementSibling.style.display='none'">
                            </div>
                            <span>${cat.name}</span>
                        </div>`;
                });

                h += `</div>
                        <button style="background:#636e72" onclick="submitLobbyVote('limit', null)">الرجوع لاختيار النقاط</button>
                    </div>`;

                document.getElementById('main-ui').innerHTML = h;
                return;
            }

            const pList = players.map(p => {
                const cards = (p.yellow_cards ? '🟨'.repeat(p.yellow_cards) : '') + (p.red_card ? '🟥' : '');
                return `<div class="score-item" style="padding:12px 15px; align-items:center;">
                    <div style="display:flex; justify-content:space-between; width:100%; align-items:center;">
                        <span style="font-weight:bold; font-size:18px;">${p.player_name}${cards}</span>
                        <span style="font-size:20px;">${(p.vote_limit && p.vote_cat) ? '✅' : '⏳'}</span>
                    </div>
                </div>`;
            }).join('');

            const lobbyCard = document.getElementById('lobby-card');
            // If already rendered, just update the player list and voting sections to avoid full refresh
            if (lobbyCard && currentRoom && currentRoom.trim().toUpperCase() === room.room_code.trim().toUpperCase()) {
                const pListContainer = document.getElementById('lobby-players-list');
                if (pListContainer) pListContainer.innerHTML = pList;

                // تحديث حالة الأزرار للمضيف
                const startBtn = document.getElementById('start-game-btn');
                if (startBtn) {
                    const allReady = players.every(p => p.vote_limit && p.vote_cat);
                    startBtn.disabled = !allReady || players.length < 3;
                    startBtn.style.opacity = startBtn.disabled ? '0.5' : '1';
                    startBtn.innerText = players.length < 3 ? 'بانتظار لاعبين (3 على الأقل)' :
                                       (!allReady ? 'بانتظار تصويت الجميع...' : 'ابدأ اللعب الآن! 🚀');
                }
                return;
            }

            const allReady = players.every(p => p.vote_limit && p.vote_cat);
            const isHost = room.host_id == currentUser.user_id;

            let h = `<div class="card" id="lobby-card">`;

            if (isHost) {
                h += `
                    <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 20px; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.1);">
                        <span style="color: #a29bfe; font-size: 14px; display: block; margin-bottom: 5px;">رمز الغرفة</span>
                        <div style="font-size: 36px; font-weight: 900; letter-spacing: 5px; color: var(--accent);">${room.room_code}</div>
                        <div style="display:flex; gap:8px; justify-content:center; margin-top:10px;">
                            <button class="btn-sm" onclick="copyRoomCode()">📋 نسخ الرمز</button>
                            <button class="btn-sm" style="background:var(--primary)" onclick="copyInviteLink()">🔗 الرابط</button>
                        </div>
                    </div>`;
            } else {
                h += `<h1 style="margin-bottom:10px; font-size:28px;">🕵️ بانتظار البداية</h1>
                      <div style="color:var(--accent); font-weight:bold; margin-bottom:20px;">تم الانضمام للغرفة بنجاح</div>`;
            }

            h += `
                    <div style="text-align: right; margin-bottom: 15px;">
                        <h3 style="margin:0;">اللاعبين في الغرفة</h3>
                    </div>

                    <div id="lobby-players-list" style="margin-bottom: 25px; display: flex; flex-direction: column; gap: 8px;">
                        ${pList}
                    </div>`;

            if (isHost) {
                h += `
                    <button id="start-game-btn"
                            style="background: linear-gradient(135deg, #2ecc71, #27ae60);"
                            ${(!allReady || players.length < 3) ? 'disabled style="opacity:0.5"' : ''}
                            onclick="startOnlineGame()">
                        ${players.length < 3 ? 'بانتظار لاعبين (3 على الأقل)' : (!allReady ? 'بانتظار تصويت الجميع...' : 'ابدأ اللعب الآن! 🚀')}
                    </button>`;
            } else {
                h += `<p style="color: #9aa0b4; font-size: 14px; margin-bottom: 20px;">
                        ${!allReady ? '⏳ ننتظر بقية اللاعبين يخلصون تصويت...' : '✅ الكل جاهز! ننتظر المضيف يبدأ اللعبة...'}
                      </p>`;
            }

            h += `<button style="background:#636e72" onclick="leaveRoom()">خروج</button>
                </div>`;

            document.getElementById('main-ui').innerHTML = h;
        }

        async function submitLobbyVote(type, value) {
            try {
                await fetch('/api/online/submit_vote', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        room_code: currentRoom,
                        user_id: currentUser.user_id,
                        type: type,
                        value: value,
                        is_lobby: true // Hint to backend to stay in waiting status
                    })
                });
                await updateRoomState();
            } catch (e) {
                console.error("Lobby vote failed", e);
            }
        }

        function showShareChoice(text, toastMsg) {
            // نستخدم متغيرات عالمية مؤقتة لتجنب مشاكل الـ escaping في الـ HTML attributes
            window._tempShareText = text;
            window._tempShareToast = toastMsg;

            const overlay = document.createElement('div');
            overlay.style = "position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:20000; display:flex; align-items:center; justify-content:center; padding:20px; box-sizing:border-box; backdrop-filter:blur(5px);";
            overlay.className = "share-overlay";
            overlay.innerHTML = `
                <div class="card" style="max-width:320px; text-align:center; border-color:var(--accent);">
                    <h2 style="margin-bottom:20px; font-size:20px;">ارسال الدعوة 💬</h2>
                    <p style="font-size:14px; color:#aaa; margin-bottom:20px;">كيف تود مشاركة الرابط مع أصدقائك؟</p>

                    <button onclick="handleCopyClick(this)" style="background:var(--primary); margin-bottom:12px; display:flex; align-items:center; justify-content:center; gap:10px;">
                        <span>📋 نسخ النص</span>
                    </button>

                    <button id="native-share-btn" style="background:var(--accent); color:#000; margin-bottom:12px; display:flex; align-items:center; justify-content:center; gap:10px;">
                        <span>📤 مشاركة عبر التطبيقات</span>
                    </button>

                    <button onclick="this.parentElement.parentElement.remove()" style="background:#636e72; margin-top:10px; border-radius:12px; padding:10px;">إلغاء</button>
                </div>
            `;
            document.body.appendChild(overlay);

            document.getElementById('native-share-btn').onclick = async () => {
                overlay.remove();
                if (navigator.share) {
                    try {
                        await navigator.share({
                            title: 'برا السالفة',
                            text: window._tempShareText
                        });
                    } catch (err) {
                        copyToClipboard(window._tempShareText, window._tempShareToast);
                    }
                } else {
                    copyToClipboard(window._tempShareText, window._tempShareToast);
                }
            };
        }

        function handleCopyClick(btn) {
            btn.parentElement.parentElement.remove();
            copyToClipboard(window._tempShareText, window._tempShareToast);
        }

        function copyInviteLink() {
            const url = window.location.origin + '?join=' + currentRoom;
            const text = `يالله تعال نلعب برا الساله الي مسويها ابو الاكبر بس ادخل للرابط\n${url}`;
            showShareChoice(text, "🔗 تم نسخ رابط الدعوة!");
        }

        function copyRoomCode() {
            if (!currentRoom) return;
            const text = `رمز الغرفة في لعبة برا السالفة هو: ${currentRoom}`;
            showShareChoice(text, "📋 تم نسخ رمز الغرفة: " + currentRoom);
        }

        function copyToClipboard(text, toastMsg) {
            navigator.clipboard.writeText(text).then(() => {
                showToast(toastMsg);
            }).catch(err => {
                const tempInput = document.createElement("input");
                tempInput.value = text;
                document.body.appendChild(tempInput);
                tempInput.select();
                document.execCommand("copy");
                document.body.removeChild(tempInput);
                showToast(toastMsg);
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
                    <div id="box" style="background:#0f0c29; padding:40px 20px; border-radius:30px; margin:20px 0; border: 2px solid var(--accent); display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 200px;">
                        <h2 style="font-size: 32px; margin-bottom: 20px; color: #fff; text-align: center;">
                            ${isSpy ? '🕵️ أنت برة السالفة!' : '🤫 السالفة هي:'}
                        </h2>
                        ${isSpy ? '' : `<h1 style="font-size: 48px; color: var(--accent); text-align: center; margin: 0;">${room.secret_word}</h1>`}
                    </div>
                    <button onclick="onlineAction('ready_role')" style="background: var(--success); font-size: 20px; padding: 15px;">فهمت، جاهز</button>
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
            const currentQ = gameData.current_q;
            const isMyTurn = gameData.current_asker_id == currentUser.user_id && !currentQ;
            const isAsker = currentQ && currentQ.asker_id == currentUser.user_id;
            const isAnswerer = currentQ && currentQ.ans_id == currentUser.user_id;
            const readyToVote = gameData.ready_to_vote || [];
            const hasOptedToVote = readyToVote.includes(currentUser.user_id);
            const timeLeft = room.time_left ?? 0;
            const me = players.find(p => p.user_id == currentUser.user_id);

            const stateKey = `${gameData.current_asker_id}_${currentQ ? currentQ.status : 'idle'}_${readyToVote.length}_${me.red_card?'red':'ok'}`;
            const questionsCard = document.getElementById('questions-card');

            // Build chat history
            let chatHtml = "";
            (gameData.q_seq || []).forEach(item => {
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
            });
            if (currentQ) {
                if (currentQ.status === 'asking') {
                    chatHtml += `<div class="chat-message-group"><div class="chat-bubble bubble-typing"><div class="bubble-sender">🙋‍♂️ ${currentQ.asker_name}:</div><div class="bubble-content">جاري كتابة السؤال... <span class="typing-dots"></span></div></div></div>`;
                } else if (currentQ.status === 'answering') {
                    chatHtml += `
                        <div class="chat-message-group">
                            <div class="chat-bubble bubble-asker"><div class="bubble-sender">🙋‍♂️ ${currentQ.asker_name}:</div><div class="bubble-content">${escapeHtml(currentQ.question)}</div></div>
                            <div class="chat-bubble bubble-typing"><div class="bubble-sender">💬 ${currentQ.ans_name}:</div><div class="bubble-content">جاري كتابة الإجابة... <span class="typing-dots"></span></div></div>
                        </div>`;
                }
            }

            if (questionsCard && questionsCard.getAttribute('data-state-key') === stateKey) {
                const scrollArea = document.getElementById('qa-chat-scroll');
                if (scrollArea && scrollArea.getAttribute('data-content-hash') !== chatHtml.length.toString()) {
                    scrollArea.innerHTML = chatHtml || '<p style="text-align:center; color:#9aa0b4; margin-top:20px;">الكل بانتظار السؤال الأول!</p>';
                    scrollArea.setAttribute('data-content-hash', chatHtml.length.toString());
                    scrollArea.scrollTop = scrollArea.scrollHeight;
                }
                const timerElem = document.getElementById('questions-timer');
                if (timerElem && Math.abs(parseInt(timerElem.getAttribute('data-val') || "0") - timeLeft) > 2) {
                    startOnlineCountdown(timeLeft, 'questions-timer', (t) => `⏱️ ${t} ثانية`);
                }
                return;
            }

            let inputHtml = "";
            if (me.red_card) {
                inputHtml = `<div class="qa-typing-status" style="color:var(--error); font-weight:bold;">❌ أنت مستبعد من هذه الجولة</div>`;
            } else if (isMyTurn) {
                inputHtml = `
                    <div style="background:rgba(0,0,0,0.2); padding:10px; border-radius:15px; width:100%;">
                        <p style="margin:0 0 10px 0; font-size:14px; text-align:center;">إنه دورك! اختر من تسأل:</p>
                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:6px;">
                            ${players.filter(p => p.user_id != currentUser.user_id && !p.red_card).map(p => `
                                <button class="vote-item" style="margin:0; padding:8px; font-size:12px;" onclick="onlineAction('choose_target', {target_id: ${p.user_id}, target_name: '${p.player_name.replace(/'/g, "\\'")}'})">
                                    ${p.player_name}
                                </button>
                            `).join('')}
                        </div>
                    </div>`;
            } else if (isAsker && currentQ.status === 'asking') {
                inputHtml = `
                    <div style="display: flex; gap: 8px; width:100%;">
                        <input id="online_q_input" placeholder="اكتب سؤالك لـ ${currentQ.ans_name}..." style="margin: 0; flex-grow: 1;">
                        <button onclick="submitOnlineQuestion()" style="margin: 0; width: auto; padding: 12px 20px;">إرسال 🚀</button>
                    </div>`;
            } else if (isAnswerer && currentQ.status === 'answering') {
                inputHtml = `
                    <div style="display: flex; gap: 8px; width:100%;">
                        <input id="online_a_input" placeholder="اكتب إجابتك هنا..." style="margin: 0; flex-grow: 1;">
                        <button onclick="submitOnlineAnswer()" style="margin: 0; width: auto; padding: 12px 20px;">إرسال 🚀</button>
                    </div>`;
            } else {
                const waiter = currentQ ? (currentQ.status === 'asking' ? currentQ.asker_name : currentQ.ans_name) : gameData.current_asker_name;
                inputHtml = `<div class="qa-typing-status">⏳ بانتظار <b style="color:var(--accent)">${waiter}</b>...</div>`;
            }

            const activeCount = players.filter(p=>!p.red_card).length;
            const voteButtonHtml = hasOptedToVote ?
                `<button disabled style="background:#3c339e; opacity:0.6; padding:8px; font-size:12px; width:auto; margin:0 auto;">✅ طلب تصويت (${readyToVote.length}/${activeCount})</button>` :
                `<button class="btn-yellow" onclick="confirmTransitionToVote()" style="padding:8px 15px; font-size:12px; width:auto; margin:0 auto; border-radius:12px; font-weight: bold;">🗳️ إنهاء الأسئلة؟</button>`;

            // إظهار الكلمة السرية للاعبين اللي مو جواسيس
            const isSpy = room.spy_id == currentUser.user_id;
            const wordDisplay = isSpy ?
                `<div style="background:rgba(235, 77, 75, 0.1); color:var(--error); padding:5px 10px; border-radius:10px; font-size:12px; font-weight:bold;">🕵️ أنت برة السالفة - حاول التمويه!</div>` :
                `<div style="background:rgba(46, 204, 113, 0.1); color:var(--success); padding:5px 10px; border-radius:10px; font-size:12px; font-weight:bold;">🤫 السالفة: ${room.secret_word} (${room.category})</div>`;

            let fullHtml = `
                <div class="qa-chat-layout">
                    <div class="qa-chat-header-main">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                            <h2 style="margin:0;">💬 السوالف</h2>
                            ${wordDisplay}
                        </div>
                        ${currentQ ? `
                            <div class="qa-current-turn">
                                <span style="color: var(--primary); font-weight: bold;">${currentQ.asker_name}</span>
                                👈
                                <span style="color: var(--error); font-weight: bold;">${currentQ.ans_name}</span>
                            </div>` : `<p style="font-size:13px; color:#9aa0b4;">بانتظار ${gameData.current_asker_name} ليختار هدفاً</p>`
                        }
                    </div>
                    <div class="qa-chat-scroll-area" id="qa-chat-scroll" data-content-hash="${chatHtml.length}">
                        ${chatHtml || '<p style="text-align:center; color:#9aa0b4; margin-top:20px;">ابدأوا الأسئلة! كشف الجاسوس يبدأ من هنا.</p>'}
                    </div>
                    <div class="qa-chat-footer-input">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <div id="questions-timer" onclick="showQuickTimerEdit()" class="qa-timer-badge" style="margin:0; cursor:pointer;">⏱️ ${timeLeft} ثانية</div>
                            ${voteButtonHtml}
                        </div>
                        <div class="qa-input-box-wrapper" style="flex-direction:column; gap:10px;">
                            ${inputHtml}
                        </div>
                    </div>
                </div>
            `;

            updateMainUI(`<div class="card" id="questions-card" data-state-key="${stateKey}" style="padding: 15px; border-radius: 20px;">${fullHtml}</div>`);
            setTimeout(() => {
                const scrollArea = document.getElementById('qa-chat-scroll');
                if (scrollArea) scrollArea.scrollTop = scrollArea.scrollHeight;
            }, 50);
            startOnlineCountdown(timeLeft, 'questions-timer', (t) => `⏱️ ${t} ثانية`);
        }

        function confirmTransitionToVote() {
            if (confirm("هل أنت متأكد أنك تريد الانتقال لمرحلة التصويت على الجاسوس؟")) {
                onlineAction('toggle_vote_ready');
            }
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
            const caught = room.game_data.spy_caught;
            const timeLeft = room.time_left ?? 0;

            if(isSpy) {
                let h = `<div id="spy-guess-timer" class="qa-timer-badge" style="margin-bottom:15px;">⏱️ وقت التخمين: ${timeLeft} ثانية</div>
                         <h3>${caught ? 'كشفوك! خمن وش السالفة؟' : 'ما كشفوك! خمن وش السالفة عشان تاخذ نقطة زيادة 🎯'}</h3>
                         <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin:20px 0;">`;
                room.game_data.guesses.forEach(g => {
                    h += `<div class="vote-item" style="margin:0; padding:15px; font-size:14px;" onclick="onlineAction('spy_guess', {guess: '${g.replace(/'/g, "\\'")}'})">${g}</div>`;
                });
                h += `</div>`;
                h += buildQAChatHistory();
                updateMainUI(`<div class="card">${h}</div>`);
                startOnlineCountdown(timeLeft, 'spy-guess-timer', (t) => `⏱️ وقت التخمين: ${t} ثانية`);
            } else {
                let h = `
                        <h1>${caught ? 'كفشتوا الجاسوس! ✅' : 'ما كفشتوا الجاسوس! ❌'}</h1>
                        <p style="font-size:18px;">اللي برة السالفة هو: <b style="color:var(--error); font-size:28px; display:block; margin:10px 0;">${spy.player_name}</b></p>
                        <div id="spy-guess-waiting-timer" style="color:var(--accent); font-weight:bold; margin:15px 0;">بانتظار تخمين الجاسوس... (${timeLeft}ث)</div>
                        <div class="shuffling">🌀</div>`;
                h += buildQAChatHistory();
                updateMainUI(`<div class="card">${h}</div>`);
                startOnlineCountdown(timeLeft, 'spy-guess-waiting-timer', (t) => `بانتظار تخمين الجاسوس... (${t}ث)`);
            }
        }

        function renderOnlineResult() {
            const {room, players} = window.roomData;
            const spy = players.find(p => p.user_id == room.spy_id);
            const spyGuess = room.game_data.spy_guess;
            const secretWord = room.secret_word;
            const spyGuessedRight = (spyGuess === secretWord);
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

            // Build guess feedback list
            let guessesHtml = `<div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px; margin:15px 0;">`;
            if (room.game_data.guesses) {
                room.game_data.guesses.forEach(g => {
                    let style = "background: rgba(255,255,255,0.05); color: #9aa0b4; border: 1px solid rgba(255,255,255,0.1);";
                    let icon = "";

                    if (g === secretWord) {
                        style = "background: var(--success); color: white; border: 2px solid white; font-weight: bold;";
                        icon = " ✅";
                    } else if (g === spyGuess && !spyGuessedRight) {
                        style = "background: var(--error); color: white; border: 1px solid white;";
                        icon = " ❌";
                    }

                    guessesHtml += `<div class="vote-item" style="margin:0; padding:10px; font-size:13px; cursor:default; ${style}">${g}${icon}</div>`;
                });
            }
            guessesHtml += `</div>`;

            const resultTitle = spyGuessedRight ? "🎉 الجاسوس ذكي وعرف السالفة!" : "🥳 كفشتوا الجاسوس وما عرف السالفة!";
            const resultColor = spyGuessedRight ? "var(--success)" : "var(--error)";

            updateMainUI(`
                <div class="card" style="padding: 20px 15px;">
                    ${gameOver ? `<h1 style="color:var(--accent); font-size:28px; margin-bottom:10px;">🏆 بطل اللعبة: ${winner ? winner.player_name : 'غير معروف'}</h1>` : ''}

                    <div style="background: rgba(0,0,0,0.2); padding: 15px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 20px;">
                        <h2 style="color:${resultColor}; margin-top:0;">${resultTitle}</h2>
                        <p style="font-size:18px; margin: 10px 0;">الجاسوس <b style="color:var(--accent)">${spy.player_name}</b> اختار: <b style="color:${resultColor}">${spyGuess || 'لم يختبر'}</b></p>
                        <p>السالفة الحقيقية كانت: <b style="color:var(--success)">${secretWord}</b></p>
                        ${guessesHtml}
                    </div>

                    <hr style="border:1px solid #3c339e; margin:20px 0;">
                    <h3 style="margin-bottom:15px;">النقاط الحالية (الهدف: ${room.win_limit}):</h3>
                    <div style="margin-bottom:25px;">${scoresList}</div>

                    <div style="display:flex; flex-direction:column; gap:10px;">
                        ${gameOver ?
                            `<button onclick="showMenu()">العودة للقائمة الرئيسية</button>` :
                            (isHost ? `<button onclick="onlineAction('new_round')">جولة جديدة 🔄</button>` : `<div class="qa-typing-status">⏳ بانتظار المضيف لبدء جولة جديدة...</div>`)
                        }
                    </div>

                    ${buildQAChatHistory()}
                </div>
            `);
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

        async function startDominoGame() {
            const {players} = window.roomData;
            const pCount = players.length;

            if (pCount !== 2 && pCount !== 4) {
                return alert(`يجب أن يكون عدد اللاعبين 2 أو 4 (الموجود الآن: ${pCount})`);
            }

            if(typeof showLoading === 'function') showLoading("جاري توزيع الأحجار وبدء اللعبة...");
            try {
                const res = await fetch('/api/domino/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({room_code: currentRoom, user_id: currentUser.user_id})
                });
                const d = await res.json();
                if(typeof hideLoading === 'function') hideLoading();
                if(!d.success) alert(d.msg || "فشل بدء اللعبة");
            } catch(e) {
                if(typeof hideLoading === 'function') hideLoading();
                console.error(e);
                alert("حدث خطأ أثناء محاولة بدء اللعبة");
            }
        }

        function changePCount(delta) {
            let current = parseInt(localStorage.getItem('pCount') || 3);
            if (isNaN(current) || current < 3) current = 3;
            let val = current + delta;

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
            el.classList.toggle('selected');
            const icon = el.querySelector('.status-icon');
            if (el.classList.contains('selected')) {
                icon.innerText = '✅';
                el.style.borderColor = 'var(--accent)';
                el.style.background = 'rgba(0, 255, 136, 0.05)';
            } else {
                icon.innerText = '⬜';
                el.style.borderColor = '';
                el.style.background = '';
            }
            updateSelectedCount();
        }

        function updateSelectedCount() {
            const items = Array.from(document.querySelectorAll('#p_selection_list .score-item'));
            window.pNamesSave = items.filter(el => el.querySelector('.status-icon').innerText === '✅')
                                     .map(el => el.querySelector('span').innerText);

            const count = window.pNamesSave.length;
            const counterEl = document.getElementById('selected_count');
            if(counterEl) counterEl.innerText = count;

            const nextBtn = document.querySelector('.btn-yellow');
            if(nextBtn) {
                nextBtn.disabled = (count < 3);
                nextBtn.style.opacity = (count >= 3) ? "1" : "0.5";
            }
            localStorage.setItem('pCount', count);
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
            const selected = Array.from(document.querySelectorAll('#p_selection_list .score-item'))
                .filter(el => el.querySelector('.status-icon').innerText === '✅')
                .map(el => el.querySelector('span').innerText);

            if (selected.length < 3) {
                showError("يرجى اختيار 3 لاعبين على الأقل.", "تنبيه");
                return;
            }

            if(btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="shuffling" style="font-size:20px; margin:0;">🌀</span> جاري التحميل...';
            }
            window.pNamesSave = selected;
            winLimit = 5; // القيمة الأساسية هي 5 دائماً
            setTimeout(() => navigateTo('setup', {step: 3}), 500);
        }

        async function showSetup(step, push = true) {
            if(push) history.pushState({screen: 'setup', step}, "");
            if(!window.pNamesSave) window.pNamesSave = [];

            if(step === 1 || step === 2) {
                // دمج اختيار عدد اللاعبين واختيارهم في صفحة واحدة
                let savedPlayers = currentUser.saved_players || [];

                let h = `<div id="p_selection_list" style="max-height: 300px; overflow-y: auto; margin-bottom: 20px; text-align: right;">`;

                savedPlayers.forEach((p, idx) => {
                    const name = typeof p === 'string' ? p : p.name;
                    const isSelected = window.pNamesSave.includes(name);
                    h += `
                        <div class="score-item ${isSelected ? 'selected' : ''}"
                             style="cursor:pointer; ${isSelected ? 'border-color:var(--accent); background:rgba(0, 255, 136, 0.05);' : ''}"
                             onclick="togglePSelection(this, '${name.replace(/'/g, "\\'")}')">
                            <span>${name}</span>
                            <span class="status-icon">${isSelected ? '✅' : '⬜'}</span>
                        </div>`;
                });
                h += `</div>`;

                h += `
                    <div style="display:flex; gap:10px; margin-bottom:15px;">
                        <input id="new_p_name" placeholder="اسم لاعب جديد" style="margin:0">
                        <button onclick="addNewPlayerToList()" style="width:80px; margin:0; background:var(--success)">+</button>
                    </div>

                    <p id="selection_info" style="margin:10px 0; font-size:18px; color:white; text-align:center; background:rgba(255,255,255,0.05); padding:10px; border-radius:15px;">
                        عدد المختارين: <span id="selected_count" style="color:var(--accent); font-weight:bold; font-size:22px;">0</span>
                    </p>

                    <button class="btn-yellow" onclick="confirmPlayersAndNext(this)">التالي: تحديد هدف الفوز</button>
                    <button style="background:#636e72" onclick="navigateTo('menu')">رجوع</button>`;

                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2>من سيلعب؟ 👥</h2>
                        <p style="font-size:13px; color:#aaa; margin-bottom:15px;">اختر اللاعبين من القائمة (3 على الأقل)</p>
                        ${h}
                    </div>`;

                updateSelectedCount();
            } else if(step === 3) {
                // عرض صفحة اختيار عدد الفوز في الاوفلاين
                // نضمن أن الخيار التلقائي هو 5
                if (winLimit === 10 || !winLimit) winLimit = 5;
                const currentWinLimit = winLimit;
                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2>🏆 هدف الفوز</h2>
                        <p style="color: #9aa0b4; margin-bottom: 20px;">حدد عدد النقاط المطلوب للفوز بالسالفة</p>

                        <div style="display: flex; gap: 10px; justify-content: center; margin-bottom: 30px;">
                            <div class="win-opt ${currentWinLimit === 5 ? 'selected' : ''}" onclick="selectWinLimit(this, 5)">5</div>
                            <div class="win-opt ${currentWinLimit === 10 ? 'selected' : ''}" onclick="selectWinLimit(this, 10)">10</div>
                            <div class="win-opt ${currentWinLimit === 15 ? 'selected' : ''}" onclick="selectWinLimit(this, 15)">15</div>
                            <div class="win-opt ${currentWinLimit === 20 ? 'selected' : ''}" onclick="selectWinLimit(this, 20)">20</div>
                        </div>
                        <input type="hidden" id="win_limit_val" value="${currentWinLimit}">

                        <button class="btn-yellow" onclick="showOfflineCategoryStep()">التالي: اختيار الفئة</button>
                        <button style="background:#636e72" onclick="navigateTo('setup', {step: 2})">رجوع</button>
                    </div>`;
            }
        }

        async function showOfflineCategoryStep() {
            // التقاط قيمة هدف الفوز من الواجهة الحالية قبل مسحها
            const winEl = document.getElementById('win_limit_val');
            if (winEl) winLimit = parseInt(winEl.value);

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
                    // التأكد من أننا لا نزال في مرحلة الإعداد ولم تبدأ اللعبة فعلياً
                    if (cats && cats.length && !isStartingGame && !game) {
                        saveCachedCategories(cats);
                        await renderCategorySelection(cats);
                        prefetchCategoryImages(cats);
                    }
                }
            } catch (err) { console.error(err); }
        }

        function selectWinLimit(el, val) {
            document.querySelectorAll('.win-opt').forEach(opt => opt.classList.remove('selected'));
            el.classList.add('selected');
            const input = document.getElementById('win_limit_val');
            if(input) input.value = val;
            winLimit = val;
            // حفظ في window أيضاً للتأكيد الإضافي
            window.winLimit = val;
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
            // منع أي تحديث للواجهة إذا بدأت اللعبة أو كانت شاشة التحميل ظاهرة
            if (isStartingGame || (game && game.players) || document.querySelector('.shuffling')) return;

            const selectedCat = document.getElementById('selected_cat')?.value;

            const thumbs = await getCachedCategoryThumbnails();

            // فحص إضافي بعد الانتظار لأن الحالة قد تتغير أثناء جلب الصور
            if (isStartingGame || (game && game.players) || document.querySelector('.shuffling')) return;

            const catsHtml = cats.map(c => {
                const thumbnail = thumbs[c.name];
                const imageUrl = c.image_url || c.image;
                const isSelected = selectedCat === c.name;
                return `
                <div class="cat-card ${isSelected ? 'selected' : ''}" data-cat-name="${c.name}">
                    ${imageUrl ? `
                        <div class="cat-image-wrapper">
                            <div class="image-placeholder">⌛</div>
                            <img src="${thumbnail || imageUrl}" alt="${c.name}">
                        </div>` : '<div class="no-img">؟</div>'}
                    <span>${c.name}</span>
                </div>`;
            }).join('');

            const mainUi = document.getElementById('main-ui');
            const existingGrid = mainUi.querySelector('.cat-grid');
            const existingCard = mainUi.querySelector('.card');

            if (existingGrid && document.getElementById('selected_cat')) {
                if (existingGrid.dataset.lastCount != cats.length) {
                    existingGrid.innerHTML = catsHtml;
                    existingGrid.dataset.lastCount = cats.length;
                    document.querySelectorAll('.cat-card').forEach(card => {
                        card.addEventListener('click', () => selectCat(card, card.dataset.catName));
                    });
                    loadCategoryImages();
                }
                if (existingCard) existingCard.style.animation = 'none';
                return;
            }

            mainUi.innerHTML = `
                <div class="card">
                    <h2>اختر نوع السالفة 📂</h2>
                    <div class="cat-grid" data-last-count="${cats.length}">${catsHtml}</div>
                    <input type="hidden" id="selected_cat" value="${selectedCat || ''}">

                    <button class="btn-yellow" onclick="startGameFinal(this)">ابدأ اللعب الآن 🚀</button>
                    <button style="background:#636e72" onclick="navigateTo('setup', {step: 3})">رجوع</button>
                </div>`;

            document.querySelectorAll('.cat-card').forEach(card => {
                card.addEventListener('click', () => selectCat(card, card.dataset.catName));
            });

            loadCategoryImages();

            // إظهار تنبيهات التحميل إذا لزم الأمر
            if (fromCache || isFallback) {
                const existingNotice = document.querySelector('.cache-notice');
                if (!existingNotice) {
                    const notice = document.createElement('div');
                    notice.className = 'cache-notice';
                    notice.style = 'margin-top:14px; color:#a9a9a9; font-size:14px;';
                    notice.textContent = fromCache ?
                        'تم عرض الفئات من الكاش المحلي، ويتم تحميل الصور تدريجياً.' :
                        'يتم عرض الفئات الأساسية أولاً، والصور تُحمّل في الخلفية.';
                    document.querySelector('.card')?.appendChild(notice);
                }
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
            const catEl = document.getElementById('selected_cat');
            const cat = catEl ? catEl.value : "";

            if(!cat) return alert("اختر فئة أولاً!");
            if (isStartingGame) return;

            isStartingGame = true; // تفعيل القفل فوراً

            // استبدال الواجهة فوراً لضمان عدم تداخل أي تحديثات أخرى
            document.getElementById('main-ui').innerHTML = `
                <div class="card" style="padding: 40px 20px;">
                    <div class="shuffling" style="font-size: 50px; margin-bottom: 20px;">🌀</div>
                    <h2 style="color: var(--accent);">جاري البدء...</h2>
                    <p style="color: #aaa;">نجهز لك السالفة والمواضيع، لحظات من فضلك</p>
                </div>`;

            start(cat);
        }

        async function start(category) {
            isStartingGame = true;
            if(document.getElementById('global-exit-btn')) document.getElementById('global-exit-btn').style.display = 'block';
            const players = window.pNamesSave || [];

            const updatedScores = {};
            players.forEach(p => {
                updatedScores[p] = totalScores[p] || 0;
            });
            totalScores = updatedScores;

            // محاولة البدء محلياً أولاً لضمان السرعة (أو في حال عدم وجود إنترنت)
            try {
                let localData = null;
                const words = CATEGORIES_DATA[category] || CATEGORIES_DATA["أكلات"];

                if (words) {
                    const correct = words[Math.floor(Math.random() * words.length)];
                    const roles = new Array(players.length).fill("in");
                    const spyIdx = Math.floor(Math.random() * players.length);
                    roles[spyIdx] = "spy";

                    const other = words.filter(w => w !== correct);
                    let guesses = [];
                    let tempOther = [...other];
                    for(let i=0; i<Math.min(other.length, 6); i++) {
                        const rIdx = Math.floor(Math.random() * tempOther.length);
                        guesses.push(tempOther.splice(rIdx, 1)[0]);
                    }
                    guesses.push(correct);
                    guesses.sort(() => Math.random() - 0.5);

                    const q_seq = [];
                    const n = players.length;
                    for (let i = 0; i < n; i += 2) {
                        if (i + 1 < n) q_seq.push({ "f": players[i], "t": players[i + 1] });
                        else q_seq.push({ "f": players[i], "t": players[0] });
                    }
                    for (let i = 0; i < n; i += 2) {
                        if (i + 1 < n) q_seq.push({ "f": players[i + 1], "t": players[(i + 2) % n] });
                    }

                    localData = { word: correct, roles, guesses, q_seq, spy_idx: spyIdx };
                }

                // إذا نجح التوليد المحلي، نستخدمه فوراً
                if (localData) {
                    game = localData;
                    game.players = players;
                    game.category = category;
                    game.curr = 0;
                    game.qIdx = 0;
                    showRole();

                    // محاولة مزامنة البدء مع السيرفر في الخلفية إذا أردت، لكننا هنا نعطي الأولوية للسرعة
                    fetch('/api/game/start', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({players, category})
                    }).catch(e => console.log("Background sync failed, using local game."));

                    return;
                }
            } catch (localErr) {
                console.warn("Local game start failed, falling back to fetch:", localErr);
            }

            // الفولباك (Fallback) للسيرفر في حال فشل المنطق المحلي
            try {
                const res = await fetch('/api/game/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({players, category})
                });
                if (!res.ok) throw new Error("فشل الاتصال بالسيرفر");
                const data = await res.json();
                game = data;
                game.players = players;
                game.category = category;
                game.curr = 0;
                game.qIdx = 0;
                showRole();
            } catch (err) {
                console.error("Start Game Error:", err);
                isStartingGame = false;
                alert("حدث خطأ أثناء بدء اللعبة. يرجى المحاولة مرة أخرى.");
                navigateTo('setup', {step: 3});
            }
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

                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1);">
                        <button onclick="confirmExitGame()" style="background:transparent; color:#ff7675; font-size:14px; padding:5px; border:none; text-decoration:underline;">❌ إنهاء اللعبة والعودة للرئيسية</button>
                    </div>
                </div>`;
        }

        function startTimer(callback, customTime = null) {
            if(timerInterval) clearInterval(timerInterval);

            // تحقق من الإعدادات المحلية للمستخدم
            const userDisabled = localStorage.getItem('user_timer_disabled') === 'true';
            const userQTimeout = parseInt(localStorage.getItem('user_question_timeout')) || 30;
            const userVTimeout = parseInt(localStorage.getItem('user_vote_timeout')) || 10;

            if (userDisabled) {
                const timerEl = document.getElementById('timer-display');
                if(timerEl) {
                    timerEl.innerText = "∞";
                    timerEl.onclick = () => showQuickTimerEdit(callback);
                    timerEl.style.cursor = "pointer";
                }
                return;
            }

            let timeLeft = customTime;
            if (timeLeft === null) {
                // تحديد الوقت التلقائي بناءً على السياق (هنا نفترض أنه سؤال إذا لم يحدد، أو نمرره يدوياً في الاستدعاءات)
                timeLeft = userQTimeout;
            }

            const timerEl = document.getElementById('timer-display');
            if(timerEl) {
                timerEl.innerText = timeLeft;
                timerEl.onclick = () => showQuickTimerEdit(callback);
                timerEl.style.cursor = "pointer";
            }

            timerInterval = setInterval(() => {
                timeLeft--;
                if(timerEl) timerEl.innerText = timeLeft;
                if(timeLeft <= 0) {
                    clearInterval(timerInterval);
                    callback();
                }
            }, 1000);
        }

        function showQuickTimerEdit(callback) {
            const currentVal = document.getElementById('timer-display').innerText;
            const newVal = prompt("تعديل الوقت المتبقي (ثانية):", currentVal === "∞" ? "30" : currentVal);

            if (newVal !== null && !isNaN(newVal)) {
                const seconds = parseInt(newVal);
                if (currentRoom) {
                    // Online Mode: Only host can adjust
                    const {room} = window.roomData;
                    if (room.host_id == currentUser.user_id) {
                        onlineAction('adjust_timer', {new_time: seconds});
                    } else {
                        alert("فقط المضيف يمكنه تعديل الوقت.");
                    }
                } else {
                    // Offline Mode: Direct adjustment
                    startTimer(callback, seconds);
                }
            }
        }

        function showPhase1() {
            if(game.qIdx >= game.q_seq.length) {
                document.getElementById('main-ui').innerHTML = `
                    <div class="card" style="animation: pop 0.3s ease;">
                        <h2 style="color:var(--accent)">انتهت الأسئلة الإجبارية! 🏁</h2>
                        <p style="margin:20px 0; font-size:18px;">انتهت الجولة، هل تريدون البدء بالتصويت أم الاستمرار في الأسئلة الحرة؟</p>
                        <button onclick="showPhase2(game.players[0])" style="background:var(--primary)">أسئلة حرة (إضافية) 🔄</button>
                        <button class="btn-yellow" onclick="startVoting()" style="font-size:22px; margin-top:10px;">انتقال للتصويت 🗳️</button>
                    </div>`;
                return;
            }
            const q = game.q_seq[game.qIdx];
            const userQTimeout = parseInt(localStorage.getItem('user_question_timeout')) || 30;
            const userDisabled = localStorage.getItem('user_timer_disabled') === 'true';

            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="q-badge">مرحلة إجبارية</span>
                        <div style="background:var(--error); padding:5px 15px; border-radius:10px; font-weight:bold;">
                            ⏱️ <span id="timer-display">${userDisabled ? '∞' : userQTimeout}</span>
                        </div>
                    </div>
                    <div style="font-size:24px; margin:30px 0;"><b style="color:#a29bfe">${q.f}</b> يسأل <b style="color:#ff7675">${q.t}</b></div>
                    <button onclick="clearInterval(timerInterval); game.qIdx++; showPhase1()">السؤال التالي</button>
                    <button style="background: #ffec00; color: #1b1464; font-weight: 900; box-shadow: 0 0 20px rgba(255, 236, 0, 0.4);" onclick="clearInterval(timerInterval); startVoting()">إنهاء الجولة والتصويت</button>
                </div>`;
            startTimer(() => {
                game.qIdx++;
                showPhase1();
            }, userQTimeout);
        }

        function showPhase2(asker, last = "") {
            const userQTimeout = parseInt(localStorage.getItem('user_question_timeout')) || 30;
            const userDisabled = localStorage.getItem('user_timer_disabled') === 'true';

            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="q-badge" style="background:var(--primary)">مرحلة الاختيار الحر</span>
                        <div style="background:var(--error); padding:5px 15px; border-radius:10px; font-weight:bold;">
                            ⏱️ <span id="timer-display">${userDisabled ? '∞' : userQTimeout}</span>
                        </div>
                    </div>
                    <h3>دور <b style="color:var(--accent)">${asker}</b> يختار مين يسأل؟</h3>
                    <div id="plist"></div>
                    <button style="margin-top:20px; background: #ffec00; color: #1b1464; font-weight: 900; box-shadow: 0 0 20px rgba(255, 236, 0, 0.4);" onclick="clearInterval(timerInterval); startVoting()">بدء التصويت</button>
                </div>`;
            game.players.forEach(p => {
                const isThreePlayers = game.players.length === 3;
                // إذا كان العدد 3، نسمح بسؤال أي شخص (حتى لو هو اللي سألنا توه) لكسر "الدائرة"
                if(p!==asker && (isThreePlayers ? true : p!==last)) {
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
                const timerEl = document.getElementById('timer-display');
                if(timerEl) {
                    timerEl.innerText = "0";
                    timerEl.parentElement.style.animation = "pulse 1s infinite";
                }
            }, userQTimeout);
        }

        function startVoting() { p_votes = {}; performVote(0); }

        function performVote(idx) {
            if(idx >= game.players.length) { showReveal(); return; }
            let list = game.players;

            // جلب وقت التصويت من إعدادات المستخدم
            const userVTimeout = parseInt(localStorage.getItem('user_vote_timeout')) || 10;
            const userDisabled = localStorage.getItem('user_timer_disabled') === 'true';

            let backBtn = idx === 0 ? `<button style="background:#636e72; margin-top:10px; border:1px solid #999;" onclick="clearInterval(timerInterval); showPhase1()">🔙 تراجع للأسئلة</button>` : "";

            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <span>مرر لـ <b>${game.players[idx]}</b></span>
                        <div style="background:var(--error); padding:5px 15px; border-radius:10px; font-weight:bold;">
                            ⏱️ <span id="timer-display">${userDisabled ? '∞' : userVTimeout}</span>
                        </div>
                    </div>
                    <p>صوت سراً: منو اللي برة السالفة؟</p>
                    <div id="vbox"></div>
                    ${backBtn}
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
                const me = game.players[idx];
                const others = game.players.filter(p => p !== me);
                const randomChoice = others[Math.floor(Math.random() * others.length)];
                p_votes[me] = randomChoice;
                performVote(idx+1);
            }, userVTimeout);
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
                if (el) {
                    el.style.background = "var(--error)";
                    el.style.boxShadow = "0 0 20px var(--error)";
                } else {
                    // إذا انتهى الوقت ولم يضغط الجاسوس، نبرز الكلمة الخطأ التي تم اختيارها عشوائياً
                    items.forEach(item => {
                        if (item.innerText === guessedWord && guessedWord !== correctWord) {
                            item.style.background = "var(--error)";
                            item.style.boxShadow = "0 0 20px var(--error)";
                        }
                    });
                }
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
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('sidebar-overlay');
            sidebar.classList.toggle('open');

            if (sidebar.classList.contains('open')) {
                overlay.style.display = 'block';
            } else {
                overlay.style.display = 'none';
            }

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

            // إضافة زر إعدادات الوقت للمستخدم في رأس القائمة
            const topDiv = document.getElementById('sidebar-dynamic-top');
            if (topDiv && !document.getElementById('user-settings-btn')) {
                let sbtn = document.createElement('button');
                sbtn.id = 'user-settings-btn';
                sbtn.innerText = "⚙️ إعدادات الوقت";
                sbtn.style.background = "rgba(255,255,255,0.1)";
                sbtn.style.marginBottom = "10px";
                sbtn.onclick = () => { toggleSidebar(); showUserSettings(); };
                topDiv.appendChild(sbtn);
            }

            if(currentUser.username_key === 'admin') {
                if(!document.getElementById('admin-btn')) {
                    let btn = document.createElement('button');
                    btn.id = 'admin-btn';
                    btn.innerText = "🛠️ لوحة الإدارة";
                    btn.style.background = "var(--accent)";
                    btn.style.color = "black";
                    btn.onclick = () => navigateTo('admin');
                    // نضعه قبل زر الإغلاق لضمان الترتيب
                    const sidebar = document.getElementById('sidebar');
                    sidebar.insertBefore(btn, sidebar.lastElementChild);
                }
            }
        } }

        function shareGame() {
            const shareData = {
                title: 'لعبة برا السالفة',
                text: 'اني العب لعبة برا السالفه ممتعة جدا تعالي خلي نلعها بس انقر ع الرابط',
                url: window.location.origin
            };

            if (navigator.share) {
                navigator.share(shareData).catch(console.error);
            } else {
                // Fallback for browsers that don't support Web Share API
                const dummy = document.createElement('input');
                document.body.appendChild(dummy);
                dummy.value = shareData.text + " " + shareData.url;
                dummy.select();
                document.execCommand('copy');
                document.body.removeChild(dummy);
                alert('تم نسخ نص المشاركة والرابط، يمكنك الآن إرسالها لأصدقائك!');
            }
        }

        async function showAdminDashboard(push = true) {
            if(push) {
                history.pushState({screen: 'admin'}, "");
                toggleSidebar();
            }
            document.getElementById('main-ui').innerHTML = `
                <div class="card admin-wide-card">
                    <h2 style="font-size:2.5rem; margin-bottom:30px;">🛠️ لوحة التحكم الإدارية</h2>
                    <div class="admin-grid">
                        <div class="admin-item-card" onclick="adminManagePlayers()" style="cursor:pointer; text-align:center; padding:50px 30px; border-radius:30px; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); transition:0.3s;">
                            <div style="font-size:5rem; margin-bottom:20px;">👥</div>
                            <h3 style="font-size:2rem; margin:15px 0; color:var(--accent);">إدارة اللاعبين</h3>
                            <p style="font-size:1.1rem; color:#aaa; line-height:1.6;">عرض وتتبع جميع اللاعبين المسجلين وتحليل نشاطهم</p>
                        </div>
                        <div class="admin-item-card" onclick="adminManageCategories()" style="cursor:pointer; text-align:center; padding:50px 30px; border-radius:30px; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); transition:0.3s;">
                            <div style="font-size:5rem; margin-bottom:20px;">📂</div>
                            <h3 style="font-size:2rem; margin:15px 0; color:var(--accent);">الفئات والكلمات</h3>
                            <p style="font-size:1.1rem; color:#aaa; line-height:1.6;">إضافة وتعديل الأقسام والكلمات وتنظيم محتوى اللعبة</p>
                        </div>
                        <div class="admin-item-card" onclick="adminManageAnnouncements()" style="cursor:pointer; text-align:center; padding:50px 30px; border-radius:30px; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); transition:0.3s;">
                            <div style="font-size:5rem; margin-bottom:20px;">📢</div>
                            <h3 style="font-size:2rem; margin:15px 0; color:var(--accent);">التحديثات والأخبار</h3>
                            <p style="font-size:1.1rem; color:#aaa; line-height:1.6;">إرسال إشعارات وتحديثات لجميع اللاعبين</p>
                        </div>
                        <div class="admin-item-card" onclick="adminManageTimeouts()" style="cursor:pointer; text-align:center; padding:50px 30px; border-radius:30px; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); transition:0.3s;">
                            <div style="font-size:5rem; margin-bottom:20px;">⏱️</div>
                            <h3 style="font-size:2rem; margin:15px 0; color:var(--accent);">الإعدادات والهوية</h3>
                            <p style="font-size:1.1rem; color:#aaa; line-height:1.6;">التحكم في المهل الزمنية، الأصوات، وتحديث أيقونة PWA</p>
                        </div>
                    </div>
                    <button style="background:#333; margin-top:50px; width:auto; padding:15px 40px; font-size:1.2rem;" onclick="navigateTo('menu')">🏠 العودة للقائمة الرئيسية</button>
                </div>`;
        }

        function adminManageAnnouncements() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>📢 إرسال تحديث جديد</h2>
                    <p style="margin-bottom:20px; color:#aaa;">سيظهر هذا التحديث لجميع اللاعبين عبر زر الجرس.</p>
                    <textarea id="announcement_text" placeholder="اكتب التحديث هنا..." style="width:100%; height:120px; padding:15px; border-radius:15px; background:#222; color:white; border:1px solid #444; margin-bottom:20px;"></textarea>
                    <button onclick="sendAnnouncement()">إرسال التحديث 🚀</button>
                    <button style="background:#636e72; margin-top:10px;" onclick="showAdminDashboard(false)">رجوع</button>
                </div>`;
        }

        async function sendAnnouncement() {
            const text = document.getElementById('announcement_text').value.trim();
            if(!text) return alert("يرجى كتابة نص");

            showLoading("جاري الإرسال...");
            try {
                const res = await fetch('/api/admin/announcements/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text})
                });
                const d = await res.json();
                if(d.success) {
                    alert("تم إرسال التحديث بنجاح ✅");
                    showAdminDashboard(false);
                } else {
                    alert("فشل الإرسال");
                }
            } catch(e) { console.error(e); alert("خطأ في الاتصال"); }
        }

        async function adminManageAnnouncements() {
            showLoading("جاري تحميل التحديثات...");
            try {
                const res = await fetch('/api/announcements');
                const announcements = await res.json();

                let html = `
                    <div class="card" style="max-height: 80vh; overflow-y: auto;">
                        <h2>📢 إدارة التحديثات</h2>

                        <div style="background:rgba(255,255,255,0.05); padding:20px; border-radius:15px; margin-bottom:30px; border:1px solid rgba(255,255,255,0.1);">
                            <h3 style="margin-top:0;">إرسال تحديث جديد</h3>
                            <textarea id="announcement_text" placeholder="اكتب التحديث هنا..." style="width:100%; height:80px; padding:12px; border-radius:12px; background:#111; color:white; border:1px solid #444; margin-bottom:15px;"></textarea>
                            <button onclick="sendAnnouncement()">إرسال التحديث 🚀</button>
                        </div>

                        <h3>التحديثات السابقة (يمكنك التعديل أو الحذف)</h3>
                        <div id="admin-announcements-list">`;

                if (!announcements || announcements.length === 0) {
                    html += `<p style="color:#aaa;">لا توجد تحديثات سابقة.</p>`;
                } else {
                    announcements.forEach(item => {
                        html += `
                            <div class="announcement-item" style="border-right-color: #f1c40f; margin-bottom:15px;">
                                <textarea id="edit_text_${item.id}" style="width:100%; background:transparent; border:none; color:white; font-size:14px; resize:none; height:60px;">${item.text}</textarea>
                                <div style="display:flex; gap:10px; margin-top:10px;">
                                    <button onclick="updateAnnouncement(${item.id})" style="padding:5px 15px; font-size:12px; background:#2ecc71;">حفظ التعديل ✅</button>
                                    <button onclick="deleteAnnouncement(${item.id})" style="padding:5px 15px; font-size:12px; background:#e74c3c;">حذف 🗑️</button>
                                </div>
                            </div>`;
                    });
                }

                html += `
                        </div>
                        <button style="margin-top:20px; background:#636e72;" onclick="showAdminDashboard(false)">رجوع</button>
                    </div>`;

                document.getElementById('main-ui').innerHTML = html;
            } catch (e) { console.error(e); alert("خطأ في التحميل"); }
        }

        async function updateAnnouncement(id) {
            const text = document.getElementById(`edit_text_${id}`).value.trim();
            if(!text) return alert("لا يمكن ترك النص فارغاً");

            showLoading("جاري الحفظ...");
            try {
                const res = await fetch('/api/admin/announcements/update', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id, text})
                });
                const d = await res.json();
                if(d.success) {
                    alert("تم تعديل التحديث بنجاح ✨");
                    adminManageAnnouncements();
                } else { alert("فشل التعديل"); }
            } catch(e) { console.error(e); }
        }

        async function deleteAnnouncement(id) {
            if(!confirm("هل أنت متأكد من حذف هذا التحديث؟")) return;

            showLoading("جاري الحذف...");
            try {
                const res = await fetch('/api/admin/announcements/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id})
                });
                const d = await res.json();
                if(d.success) {
                    alert("تم الحذف بنجاح");
                    adminManageAnnouncements();
                } else { alert("فشل الحذف"); }
            } catch(e) { console.error(e); }
        }

        async function sendAnnouncement() {
            const text = document.getElementById('announcement_text').value.trim();
            if(!text) return alert("يرجى كتابة نص");

            showLoading("جاري الإرسال...");
            try {
                const res = await fetch('/api/admin/announcements/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text})
                });
                const d = await res.json();
                if(d.success) {
                    alert("تم إرسال التحديث بنجاح ✅");
                    adminManageAnnouncements();
                } else {
                    alert("فشل الإرسال");
                }
            } catch(e) { console.error(e); alert("خطأ في الاتصال"); }
        }

        function adminManageTimeouts() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card admin-wide-card">
                    <h2>⏱️ إعدادات الأصوات والهوية</h2>
                    <div class="admin-content-box">
                        <h3 class="admin-section-title">روابط الأصوات (URL)</h3>
                        <div class="admin-setting-row full-width">
                            <label>صوت النقر/التالي:</label>
                            <div class="admin-input-group">
                                <input type="text" id="sound_click_setting" value="${soundClickUrl}" dir="ltr">
                                <button onclick="saveAdminSetting('sound_click', 'sound_click_setting')" class="admin-save-btn">حفظ</button>
                            </div>
                        </div>
                        <div class="admin-setting-row full-width">
                            <label>صوت كشف الدور:</label>
                            <div class="admin-input-group">
                                <input type="text" id="sound_reveal_setting" value="${soundRevealUrl}" dir="ltr">
                                <button onclick="saveAdminSetting('sound_reveal', 'sound_reveal_setting')" class="admin-save-btn">حفظ</button>
                            </div>
                        </div>
                        <div class="admin-setting-row full-width">
                            <label>صوت الفوز:</label>
                            <div class="admin-input-group">
                                <input type="text" id="sound_win_setting" value="${soundWinUrl}" dir="ltr">
                                <button onclick="saveAdminSetting('sound_win', 'sound_win_setting')" class="admin-save-btn">حفظ</button>
                            </div>
                        </div>
                        <div class="admin-setting-row full-width">
                            <label>صوت الخطأ/الفشل:</label>
                            <div class="admin-input-group">
                                <input type="text" id="sound_fail_setting" value="${soundFailUrl}" dir="ltr">
                                <button onclick="saveAdminSetting('sound_fail', 'sound_fail_setting')" class="admin-save-btn">حفظ</button>
                            </div>
                        </div>

                        <h3 class="admin-section-title">هوية التطبيق (PWA)</h3>
                        <div class="admin-setting-row full-width">
                            <label>أيقونة التطبيق (PNG):</label>
                            <div class="admin-upload-box">
                                <input type="file" id="app_icon_file" accept="image/png,image/jpeg">
                                <button onclick="handleIconUpload()" class="admin-upload-btn">تحديث الأيقونة عند الجميع</button>
                            </div>
                        </div>
                    </div>
                    <button style="background:#636e72; margin-top:20px;" onclick="showAdminDashboard(false)">رجوع</button>
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
                if(key === 'sound_click') { soundClickUrl = val; sounds.click = new Audio(val); }
                if(key === 'sound_reveal') { soundRevealUrl = val; sounds.reveal = new Audio(val); }
                if(key === 'sound_win') { soundWinUrl = val; sounds.win = new Audio(val); }
                if(key === 'sound_fail') { soundFailUrl = val; sounds.fail = new Audio(val); }
                alert("تم التحديث بنجاح ✅");
            }
        }

        function showUserSettings() {
            const qTime = localStorage.getItem('user_question_timeout') || 30;
            const vTime = localStorage.getItem('user_vote_timeout') || 10;
            const isDisabled = localStorage.getItem('user_timer_disabled') === 'true';

            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2 style="color:var(--accent); margin-bottom:20px;">⚙️ إعدادات الوقت الخاصة بك</h2>
                    <p style="font-size:0.9rem; color:#aaa; margin-bottom:20px;">هذه الإعدادات تؤثر على جهازك فقط.</p>

                    <div class="admin-content-box" style="background:rgba(255,255,255,0.05); padding:20px; border-radius:15px;">
                        <div style="margin-bottom:15px;">
                            <label style="display:block; margin-bottom:5px;">وقت السؤال (ثانية):</label>
                            <input type="number" id="u_q_time" value="${qTime}" style="width:100%; padding:10px; border-radius:8px; border:1px solid #444; background:#222; color:white;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="display:block; margin-bottom:5px;">وقت التصويت (ثانية):</label>
                            <input type="number" id="u_v_time" value="${vTime}" style="width:100%; padding:10px; border-radius:8px; border:1px solid #444; background:#222; color:white;">
                        </div>
                        <div style="display:flex; align-items:center; gap:10px; margin-top:20px;">
                            <input type="checkbox" id="u_t_disable" ${isDisabled ? 'checked' : ''} style="width:20px; height:20px;">
                            <label for="u_t_disable">إيقاف المؤقت نهائياً</label>
                        </div>
                    </div>

                    <button onclick="saveUserSettings()" style="margin-top:20px;">حفظ الإعدادات</button>
                    <button style="background:#636e72; margin-top:10px;" onclick="navigateTo('menu')">إلغاء</button>
                </div>`;
        }

        function saveUserSettings() {
            localStorage.setItem('user_question_timeout', document.getElementById('u_q_time').value);
            localStorage.setItem('user_vote_timeout', document.getElementById('u_v_time').value);
            localStorage.setItem('user_timer_disabled', document.getElementById('u_t_disable').checked);
            alert("تم حفظ إعداداتك الشخصية بنجاح ✅");
            navigateTo('menu');
        }

        async function handleIconUpload() {
            const fileInput = document.getElementById('app_icon_file');
            if(!fileInput.files[0]) return alert("يرجى اختيار ملف أولاً");

            showLoading("جارٍ ضغط ورفع الأيقونة...");
            try {
                // ضغط الصورة لضمان حجم صغير وجودة مناسبة للأيقونة (512x512)
                const compressedDataUrl = await compressImageFile(fileInput.files[0], 0.8, 512, 512);

                // تحويل الـ DataURL إلى Blob لإرساله كملف
                const blob = await (await fetch(compressedDataUrl)).blob();

                const formData = new FormData();
                formData.append('icon', blob, 'icon.png');

                const res = await fetch('/api/admin/upload_icon', {
                    method: 'POST',
                    body: formData
                });
                const d = await res.json();
                if(d.success) {
                    alert("تم تحديث أيقونة التطبيق بنجاح! سيلاحظ المستخدمون التغيير عند فتح التطبيق مجدداً. ✅");
                    adminManageTimeouts();
                } else {
                    alert("خطأ: " + d.msg);
                    adminManageTimeouts();
                }
            } catch(e) {
                console.error(e);
                alert("فشل الرفع: تأكد من اختيار ملف صورة صحيح");
                adminManageTimeouts();
            }
        }

        async function adminManagePlayers() {
            try {
                showLoading("لوحة الإدارة - جاري تحميل اللاعبين...");
                const res = await fetch('/api/admin/players');
                if (!res.ok) throw new Error("فشل الاتصال بالسيرفر");
                const players = await res.json();
                let h = `<h2>👥 قائمة اللاعبين</h2>
                    <div class="admin-content-box" style="background:transparent; padding:0; margin-top:10px;">
                        <div class="admin-grid" style="max-height:80vh; overflow-y:auto; padding:10px;">`;

                // تمت إزالة الترتيب من هنا لأنه يتم الآن في السيرفر لسرعة الاستجابة

                players.forEach(p => {
                    const safePlayerName = escapeHtml(p.player_name);
                    const safeUsernameKey = escapeHtml(p.username_key);
                    h += `<div class="admin-item-card" style="padding:20px; border-radius:20px; background:rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.05); transition: 0.3s ease;">
                        <div style="display:flex; align-items:center; gap:15px; margin-bottom:15px;">
                            <div style="width:55px; height:55px; border-radius:15px; background:linear-gradient(135deg, var(--primary), var(--accent)); display:flex; align-items:center; justify-content:center; font-size:1.4rem; color:#050505; font-weight:900; box-shadow: 0 5px 15px rgba(0, 210, 255, 0.3);">
                                ${safePlayerName.charAt(0).toUpperCase()}
                            </div>
                            <div style="text-align:right; flex:1; overflow:hidden;">
                                <div style="font-size:1.2rem; font-weight:bold; color:white; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${safePlayerName}</div>
                                <div style="font-size:0.9rem; color:var(--primary); opacity:0.8; font-family:monospace;">@${safeUsernameKey}</div>
                            </div>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(0,0,0,0.3); padding:12px 20px; border-radius:15px; border: 1px solid rgba(255,255,255,0.05);">
                            <span style="font-size:0.9rem; opacity:0.7;">إجمالي الانتصارات</span>
                            <b style="font-size:1.5rem; color:var(--success); text-shadow: 0 0 10px rgba(46, 204, 113, 0.3);">${p.total_wins || 0}</b>
                        </div>
                    </div>`;
                });

                if(players.length === 0) h += `<p style="text-align:center; padding:40px; opacity:0.5;">لا يوجد لاعبين مسجلين حالياً</p>`;

                h += `</div></div><button style="margin-top:20px; background:#333;" onclick="showAdminDashboard(false)">🔙 العودة للوحة التحكم</button>`;
                document.getElementById('main-ui').innerHTML = `<div class="card admin-wide-card">${h}</div>`;
            } catch (err) {
                console.error('Failed to load admin players:', err);
                document.getElementById('main-ui').innerHTML = `
                    <div class="card admin-wide-card">
                        <h2>حدث خطأ أثناء تحميل اللاعبين</h2>
                        <p>${err.message || err}</p>
                        <button onclick="showAdminDashboard(false)">رجوع</button>
                    </div>`;
            }
        }

        async function adminManageCategories() {
            try {
                showLoading("لوحة الإدارة - جاري تحميل الفئات...");
                const res = await fetch('/api/categories');
                if (!res.ok) throw new Error("فشل تحميل البيانات من السيرفر");
                const cats = await res.json();
                let h = `<h2>📂 إدارة الفئات</h2>
                    <button style="background:var(--success); margin-bottom:15px; width:auto; padding:10px 25px;" onclick="showAddCategoryForm()">➕ إضافة فئة جديدة</button>
                    <div id="cat-form-container"></div>
                    <div class="admin-grid" style="max-height:60vh; overflow-y:auto; padding:5px;">`;
                cats.forEach(c => {
                    const catJson = JSON.stringify(c).replace(/"/g, '&quot;');
                    const catNameJson = JSON.stringify(c.name).replace(/"/g, '&quot;');
                    h += `<div class="admin-item-card">
                        <div style="display:flex; align-items:center; gap:15px;">
                            ${c.image_url ? `<img src="${c.image_url}" style="width:60px; height:60px; border-radius:15px; object-fit:cover; border:2px solid rgba(255,255,255,0.1);">` : `<div style="width:60px; height:60px; border-radius:15px; background:rgba(255,255,255,0.05); display:flex; align-items:center; justify-content:center; font-size:1.5rem;">📦</div>`}
                            <div style="flex:1;">
                                <b style="font-size:1.2rem; color:var(--accent);">${c.name}</b>
                                <div style="font-size:0.85rem; opacity:0.7;">الترتيب: ${c.display_order}</div>
                            </div>
                        </div>
                        <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:8px; margin-top:5px;">
                            <button style="margin:0; background:var(--success); padding:8px 0;" onclick="manageWords(${catNameJson})">📝 الكلمات</button>
                            <button style="margin:0; background:var(--primary); padding:8px 0;" onclick="editCategory(${catJson})">✏️ تعديل</button>
                            <button style="margin:0; background:var(--error); padding:8px 0;" onclick="deleteCategory(${c.id})">🗑️ حذف</button>
                        </div>
                    </div>`;
                });
                h += `</div><button style="margin-top:20px;" onclick="showAdminDashboard(false)">رجوع للوحة التحكم</button>`;
                document.getElementById('main-ui').innerHTML = `<div class="card admin-wide-card">${h}</div>`;
            } catch (err) {
                console.error('Failed to load admin categories:', err);
                document.getElementById('main-ui').innerHTML = `
                    <div class="card admin-wide-card">
                        <h2>حدث خطأ أثناء تحميل الفئات</h2>
                        <p>${err.message || err}</p>
                        <button onclick="showAdminDashboard(false)">رجوع</button>
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

            const d = await res.json();
            if (d.success) {
                resetCatForm();
                adminManageCategories();
            } else {
                alert("خطأ: " + (d.msg || "فشل الحفظ"));
            }
        }

        async function deleteCategory(id) {
            if(!confirm("هل أنت متأكد من حذف هذه الفئة وكل كلماتها؟")) return;
            try {
                const res = await fetch('/api/admin/category/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id})
                });
                const d = await res.json();
                if(d.success) adminManageCategories();
                else alert("خطأ: " + (d.msg || "فشل الحذف"));
            } catch (e) {
                console.error(e);
                alert("فشل الاتصال بالسيرفر");
            }
        }

        async function manageWords(catName) {
            try {
                showLoading("لوحة الإدارة - جاري تحميل الكلمات...");
                const res = await fetch('/api/admin/words');
                if (!res.ok) throw new Error("فشل تحميل الكلمات من السيرفر");
                const allWords = await res.json();
                const cleanCatName = catName.trim();
                const words = allWords.filter(w => (w.category || "").trim() === cleanCatName);

                const catEscaped = JSON.stringify(catName).replace(/"/g, "&quot;");

                let h = `<h2>📝 كلمات قسم: ${catName}</h2>
                    <div id="word-form-container" class="admin-content-box" style="margin-top:0;">
                        <div style="display:flex; flex-direction:column; gap:15px;">
                            <input id="word_id" type="hidden">
                            <textarea id="new_word_val" placeholder="أدخل الكلمات هنا... كل كلمة في سطر منفصل لإضافة مجموعة كبيرة مرة واحدة" style="width:100%; min-height:120px; padding:15px; border-radius:15px; background:rgba(0,0,0,0.2); color:white; border:1px solid rgba(255,255,255,0.1); font-size:1.1rem; resize:vertical;"></textarea>
                            <div style="display:flex; gap:10px;">
                                <button id="word-save-btn" style="margin:0; background:var(--success); flex:1;" onclick="addWordToCat(${catEscaped})">➕ إضافة للقسم</button>
                                <button id="word-cancel-btn" style="background:#636e72; display:none; margin:0;" onclick="resetWordForm(${catEscaped})">إلغاء التعديل</button>
                            </div>
                        </div>
                    </div>

                    <div class="admin-content-box">
                        <div class="word-grid" id="words-container">`;

                if (words.length === 0) {
                    h += `<p id="no-words-msg" style="grid-column: 1/-1; text-align:center; color:#888; padding:20px;">لا توجد كلمات في هذا القسم حالياً.</p>`;
                }

                words.forEach(w => {
                    const wordEscaped = JSON.stringify(w.word).replace(/"/g, "&quot;");
                    h += `<div class="word-chip" id="word-item-${w.id}">
                        <span style="font-weight:bold;">${w.word}</span>
                        <div style="display:flex; gap:8px;">
                            <span style="cursor:pointer; color:var(--primary);" onclick="editWord(${w.id}, ${wordEscaped}, ${catEscaped})">✏️</span>
                            <span style="cursor:pointer; color:var(--error);" onclick="deleteWord(${w.id}, ${catEscaped})">🗑️</span>
                        </div>
                    </div>`;
                });
                h += `</div></div><button style="margin-top:10px;" onclick="adminManageCategories()">🔙 العودة للفئات</button>`;
                document.getElementById('main-ui').innerHTML = `<div class="card admin-wide-card">${h}</div>`;
            } catch (err) {
                console.error('Failed to load words for category:', err);
                document.getElementById('main-ui').innerHTML = `
                    <div class="card admin-wide-card">
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
            try {
                const res = await fetch('/api/admin/word/update', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id, word})
                });
                const d = await res.json();
                if(d.success) manageWords(catName);
                else alert("خطأ: " + (d.msg || "فشل التحديث"));
            } catch (e) {
                console.error(e);
                alert("فشل الاتصال بالسيرفر");
            }
        }

        async function addWordToCat(cat) {
            const word = document.getElementById('new_word_val').value.trim();
            if(!word) return;
            try {
                const res = await fetch('/api/admin/add_word', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({category: cat, word})
                });
                const d = await res.json();
                if(d.success) {
                    document.getElementById('new_word_val').value = "";
                    manageWords(cat);
                } else {
                    alert("خطأ: " + (d.msg || "فشل الإضافة"));
                }
            } catch (e) {
                console.error(e);
                alert("فشل الاتصال بالسيرفر");
            }
        }

        async function deleteWord(id, cat) {
            if(!confirm("هل أنت متأكد من حذف هذه الكلمة؟")) return;
            try {
                const res = await fetch('/api/admin/word/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id})
                });
                const d = await res.json();
                if(d.success) manageWords(cat);
                else alert("خطأ: " + (d.msg || "فشل الحذف"));
            } catch (e) {
                console.error(e);
                alert("فشل الاتصال بالسيرفر");
            }
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
                    window.pNamesSave = [];
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
                navigator.serviceWorker.register('/sw.js?v=10')
                    .then(reg => {
                        console.log('SW Registered', reg);
                        reg.onupdatefound = () => {
                            const installingWorker = reg.installing;
                            installingWorker.onstatechange = () => {
                                if (installingWorker.state === 'installed') {
                                    if (navigator.serviceWorker.controller) {
                                        showToast("✨ تحديث جديد متوفر! جاري التحديث...", "success");
                                        setTimeout(() => {
                                            window.location.reload();
                                        }, 2000);
                                    }
                                }
                            };
                        };
                    })
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

        // ==========================================
        //         لعبة الأونو أونلاين (UNO ONLINE)
        // ==========================================

        function showUnoMenu() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card" style="border-color: #ff7675; box-shadow: 0 0 30px rgba(255, 118, 117, 0.25);">
                    <button id="announcement-bell" class="bell-btn" onclick="showAnnouncements()">
                        🔔
                        <div class="bell-badge"></div>
                    </button>
                    <div style="font-size: 60px; margin-bottom: 20px;">🃏</div>
                    <h1 style="color:#ff7675; margin-bottom:10px;">أونو أونلاين</h1>
                    <p style="color:#aaa; margin-bottom:25px;">العب أونو مع أصدقائك مباشرة وتنافس للفوز بالنقاط!</p>

                    <button onclick="createUnoRoom()" style="background: linear-gradient(135deg, #ff7675, #d63031); margin-bottom:15px; font-weight: bold;">✨ إنشاء غرفة جديدة</button>
                    <button onclick="showUnoJoinInput()" style="background:var(--primary); margin-bottom:15px;">🚪 انضمام لغرفة</button>

                    <button style="background:#636e72; margin-top:20px;" onclick="showGameSelection()">رجوع</button>
                </div>`;
            checkAnnouncements();
        }

        let selectedUnoPlayers = 4;

        function changePlayerCount(delta) {
            selectedUnoPlayers += delta;
            if (selectedUnoPlayers < 2) selectedUnoPlayers = 2;
            if (selectedUnoPlayers > 10) selectedUnoPlayers = 10;
            
            const display = document.getElementById('player-count-display');
            if (display) {
                let text = "";
                if (selectedUnoPlayers === 2) {
                    text = "لاعبَين 👥";
                } else {
                    text = `${selectedUnoPlayers} لاعبين 👥`;
                }
                display.innerHTML = text;
            }
        }

        function submitUnoWithSelectedCount() {
            submitCreateUno(selectedUnoPlayers);
        }

        function createUnoRoom() {
            if (!currentUser) return alert("سجل دخولك أولاً");
            selectedUnoPlayers = 4;
            document.getElementById('main-ui').innerHTML = `
                <div class="card" style="border-color: #ff7675; max-width: 400px; margin: 0 auto;">
                    <h2>إعداد غرفة الأونو</h2>
                    <p style="margin-bottom:20px; color:#aaa;">حدد الحد الأقصى لعدد اللاعبين (من 2 إلى 10):</p>
                    
                    <div style="display:flex; align-items:center; justify-content:center; gap:20px; margin:25px 0; direction:ltr;">
                        <button onclick="changePlayerCount(-1)" style="width: 55px; height: 55px; border-radius: 50%; font-size: 24px; background: #ff7675; color: white; display: flex; align-items: center; justify-content: center; padding: 0; margin: 0; box-shadow: 0 4px 15px rgba(255, 118, 117, 0.3); cursor: pointer; touch-action: manipulation; border: none; font-weight: bold; width:55px !important; min-width:55px; max-width:55px;">-</button>
                        
                        <div id="player-count-display" style="font-size: 28px; font-weight: bold; min-width: 140px; color: white; text-align: center; direction: rtl;">4 لاعبين 👥</div>
                        
                        <button onclick="changePlayerCount(1)" style="width: 55px; height: 55px; border-radius: 50%; font-size: 24px; background: #2ecc71; color: white; display: flex; align-items: center; justify-content: center; padding: 0; margin: 0; box-shadow: 0 4px 15px rgba(46, 204, 113, 0.3); cursor: pointer; touch-action: manipulation; border: none; font-weight: bold; width:55px !important; min-width:55px; max-width:55px;">+</button>
                    </div>
                    
                    <button onclick="submitUnoWithSelectedCount()" style="background: linear-gradient(135deg, #ff7675, #d63031); font-weight: bold; margin-bottom: 15px; font-size: 18px; padding: 16px; box-shadow: 0 5px 15px rgba(255, 118, 117, 0.3); cursor: pointer; touch-action: manipulation; border-radius: 18px; border: none; color: white; width:100%;">🎮 إنشاء الغرفة وتأكيد اللعب</button>
                    
                    <button onclick="showUnoMenu()" style="background: #636e72; padding: 12px; cursor: pointer; touch-action: manipulation; width: 100%; border-radius: 18px; border: none; color: white; font-weight: bold;">إلغاء</button>
                </div>`;
        }

        async function submitCreateUno(maxPlayers) {
            if (!currentUser) return alert("سجل دخولك أولاً");
            
            const mainUi = document.getElementById('main-ui');
            const originalContent = mainUi.innerHTML;
            mainUi.innerHTML = `
                <div class="card" style="border-color: #ff7675;">
                    <div class="loading-spinner" style="margin: 20px auto; border-top-color: #ff7675;"></div>
                    <h2 style="color:#ff7675">جاري إنشاء الغرفة...</h2>
                    <p style="color:#aaa;">لحظات ويجهز رمز اللعب 🚀</p>
                </div>`;
            
            try {
                const res = await fetch('/api/uno/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        user_id: currentUser.user_id,
                        player_name: currentUser.player_name,
                        max_players: maxPlayers
                    })
                });
                const d = await res.json();
                if(d.success) {
                    enterRoom(d.room_code);
                } else {
                    alert(d.msg || "حدث خطأ");
                    mainUi.innerHTML = originalContent;
                }
            } catch(e) { 
                console.error(e); 
                alert("حدث خطأ في الاتصال بالسيرفر. يرجى المحاولة مرة أخرى.");
                mainUi.innerHTML = originalContent;
            }
        }

        function showUnoJoinInput() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card" style="border-color: #ff7675;">
                    <h2 style="color:#ff7675">انضمام لغرفة أونو</h2>
                    <p style="margin-bottom:20px;">أدخل رمز الغرفة المكون من 4 أحرف:</p>
                    <input id="uno_join_code" placeholder="مثلاً: ABCD" style="text-transform:uppercase; text-align:center; font-size:24px; margin-bottom:20px; width:100%; letter-spacing:5px;">
                    <button id="uno-join-btn-final" onclick="joinUnoRoom()" style="background:var(--success); font-weight:bold; cursor: pointer; touch-action: manipulation; border-radius: 18px; padding: 14px; width:100%; border:none; color:white;">انضمام الآن 🚪</button>
                    <button onclick="showUnoMenu()" style="background:#636e72; margin-top:10px; cursor: pointer; touch-action: manipulation; border-radius: 18px; padding: 12px; width:100%; border:none; color:white; font-weight:bold;">رجوع</button>
                </div>`;
            setTimeout(() => document.getElementById('uno_join_code').focus(), 100);
        }

        async function joinUnoRoom() {
            if (!currentUser) return alert("سجل دخولك أولاً");
            
            const codeInput = document.getElementById('uno_join_code');
            const code = codeInput.value.trim().toUpperCase();
            if(!code) return alert("الرجاء إدخال رمز الغرفة");
            
            const joinBtn = document.getElementById('uno-join-btn-final');
            const originalText = joinBtn ? joinBtn.innerHTML : "انضمام الآن 🚪";
            if (joinBtn) {
                joinBtn.disabled = true;
                joinBtn.innerHTML = "🌀 جاري الانضمام...";
            }
            
            try {
                const res = await fetch('/api/online/join', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        room_code: code,
                        user_id: currentUser.user_id,
                        player_name: currentUser.player_name
                    })
                });
                const d = await res.json();
                if(d.success) {
                    enterRoom(code);
                } else {
                    alert(d.msg || "تعذر الانضمام");
                    if (joinBtn) {
                        joinBtn.disabled = false;
                        joinBtn.innerHTML = originalText;
                    }
                }
            } catch(e) { 
                console.error(e); 
                alert("حدث خطأ في الاتصال بالسيرفر. يرجى المحاولة مرة أخرى.");
                if (joinBtn) {
                    joinBtn.disabled = false;
                    joinBtn.innerHTML = originalText;
                }
            }
        }

        function renderUnoLobby() {
            const {room, players} = window.roomData;
            const isHost = room.host_id == currentUser.user_id;

            let playersHTML = players.map(p => `
                <div style="background:rgba(255,255,255,0.05); padding:10px; border-radius:10px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
                    <span>👤 ${p.player_name} ${p.user_id == room.host_id ? '👑' : ''}</span>
                    <span style="color:var(--success); font-size:12px;">متصل</span>
                </div>
            `).join('');

            document.getElementById('main-ui').innerHTML = `
                <div class="card" style="border-color: #ff7675;">
                    <h2 style="color:#ff7675">غرفة انتظار أونو 🃏</h2>
                    <p style="font-size:14px; color:#aaa;">الرمز: <b style="color:white; font-size:18px;">${room.room_code}</b></p>

                    <div style="margin:20px 0; background:rgba(0,0,0,0.2); padding:15px; border-radius:15px; text-align:right;">
                        <h4 style="margin-top:0; border-bottom:1px solid #333; padding-bottom:5px;">اللاعبين (${players.length}/${room.max_players})</h4>
                        ${playersHTML}
                    </div>

                    ${isHost ? `
                        <button id="start-uno-btn" onclick="startUnoGame()" style="background:var(--success); margin-bottom:15px; cursor: pointer; touch-action: manipulation; font-weight: bold; font-size: 18px; padding: 16px; border-radius: 18px;">
                            🚀 ابدأ اللعب الآن!
                        </button>
                    ` : `
                        <div style="background:rgba(241,196,15,0.1); color:#f1c40f; padding:12px; border-radius:12px; font-size:15px; margin-bottom:15px; font-weight: bold; text-align: center;">
                            ⏳ بانتظار المضيف لبدء اللعبة...
                        </div>
                    `}
                    <button onclick="leaveRoom()" style="background:var(--error); width:100%; cursor: pointer; touch-action: manipulation; font-weight: bold; border-radius: 18px; padding: 14px;">🚪 مغادرة الغرفة</button>
                </div>`;
        }

        async function startUnoGame() {
            const roomCode = currentRoom || (window.roomData && window.roomData.room && window.roomData.room.room_code);
            const userId = currentUser && currentUser.user_id;
            const { players } = window.roomData || { players: [] };
            
            if (players.length < 2) {
                alert("يجب انضمام لاعبين اثنين على الأقل لبدء اللعب 👥. شارك رمز الغرفة مع أصدقائك!");
                return;
            }
            
            if (!roomCode || !userId) {
                alert("تعذر تحديد بيانات الغرفة أو المستخدم. يرجى محاولة إعادة الدخول.");
                return;
            }
            
            const startBtn = document.getElementById('start-uno-btn');
            if (startBtn) {
                startBtn.disabled = true;
                startBtn.innerHTML = "🌀 جاري بدء اللعبة وتوزيع الكروت...";
            }
            
            try {
                const res = await fetch('/api/uno/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        room_code: roomCode,
                        user_id: userId
                    })
                });
                const d = await res.json();
                if(!d.success) {
                    alert(d.msg || "حدث خطأ");
                    if (startBtn) {
                        startBtn.disabled = false;
                        startBtn.innerHTML = "🚀 ابدأ اللعب الآن!";
                    }
                } else {
                    await updateRoomState();
                }
            } catch(e) { 
                console.error(e); 
                alert("حدث خطأ في الاتصال بالسيرفر. يرجى المحاولة مرة أخرى.");
                if (startBtn) {
                    startBtn.disabled = false;
                    startBtn.innerHTML = "🚀 ابدأ اللعب الآن!";
                }
            }
        }

        function checkUnoValidityJS(card, topCard, currentColor) {
            if (card.includes("جوكر") || card.includes("🌈") || card.includes("🔥") || card.includes("💧") || card.includes("🌊")) return true;
            const parts = card.split(" ");
            if (parts.length < 2) return false;
            const cColor = parts[0];
            const cValue = parts[1];
            if (cColor === currentColor) return true;
            
            const topParts = topCard.split(" ");
            const topValue = topParts.length > 1 ? topParts[1] : topParts[0];
            if (cValue === topValue) return true;
            return false;
        }

        function getUnoCardColorHex(card) {
            if (card.startsWith("🔴")) return "#d63031";
            if (card.startsWith("🔵")) return "#0984e3";
            if (card.startsWith("🟡")) return "#fdcb6e";
            if (card.startsWith("🟢")) return "#2ecc71";
            return "linear-gradient(135deg, #2d3436 0%, #000 100%)";
        }

        function getUnoCardHTML(card, isPlayable, onClickAction) {
            let color = getUnoCardColorHex(card);
            let label = card;
            let borderStyle = "";
            let textColor = "white";
            
            if (card.startsWith("🔴")) label = card.replace("🔴", "").trim();
            else if (card.startsWith("🔵")) label = card.replace("🔵", "").trim();
            else if (card.startsWith("🟡")) { label = card.replace("🟡", "").trim(); textColor = "#2d3436"; }
            else if (card.startsWith("🟢")) label = card.replace("🟢", "").trim();
            else if (card.includes("جوكر")) {
                borderStyle = "border: 2px solid #ff7675;";
            }
            
            const cursorStyle = isPlayable ? "cursor: pointer;" : "opacity: 0.55; cursor: not-allowed; transform: scale(0.95);";
            const clickAttr = isPlayable && onClickAction ? `onclick="${onClickAction}"` : "";
            const glowStyle = isPlayable ? "box-shadow: 0 0 15px rgba(255,255,255,0.4);" : "";
            
            return `
                <div class="uno-card-element" ${clickAttr} style="background: ${color}; ${cursorStyle} ${glowStyle} ${borderStyle} color: ${textColor};">
                    <div class="uno-card-inner" style="border-color: ${textColor === 'white' ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.2)'};">
                        <span class="uno-card-value">${label}</span>
                    </div>
                </div>
            `;
        }

        function renderUnoGame() {
            if(!window.roomData) return;
            const {room, players} = window.roomData;
            const gd = room.game_data;
            const me = players.find(p => p.user_id == currentUser.user_id);
            const myId = String(currentUser.user_id);
            const myHand = gd.hands[myId] || [];

            const isMyTurn = gd.ordered_ids[gd.turn_index] == currentUser.user_id;
            const currentTurnPlayer = players.find(p => p.user_id == gd.ordered_ids[gd.turn_index]);

            // 1. Finished State View
            if (room.status === 'finished' || gd.phase === 'finished') {
                const winner = players.find(p => p.user_id == gd.winner_id);
                
                let scoresHTML = players.map(p => `
                    <div style="background:rgba(255,255,255,0.05); padding:10px; border-radius:10px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
                        <span>👤 ${p.player_name}</span>
                        <span style="font-weight:bold; color:var(--accent);">${p.score} نقطة</span>
                    </div>
                `).join('');

                document.getElementById('main-ui').innerHTML = `
                    <div class="card" style="border-color: var(--success); text-align:center;">
                        <h1 style="color:var(--success); font-size:40px; margin-bottom:10px;">🎉 الجولة انتهت!</h1>
                        <p style="font-size:18px;">الفائز في هذه الجولة هو: <b style="color:var(--accent); font-size:24px;">${winner ? winner.player_name : 'غير معروف'}</b></p>
                        
                        <div style="margin:25px 0; background:rgba(0,0,0,0.2); padding:15px; border-radius:15px; text-align:right;">
                            <h4 style="margin-top:0; border-bottom:1px solid #333; padding-bottom:5px;">جدول النقاط الحالي</h4>
                            ${scoresHTML}
                        </div>

                        ${room.host_id == currentUser.user_id ? `
                            <button onclick="startUnoGame()" style="background:var(--success); margin-bottom:15px; width:100%;">🔄 جولة جديدة</button>
                        ` : `
                            <div style="background:rgba(241,196,15,0.1); color:#f1c40f; padding:10px; border-radius:10px; font-size:14px; margin-bottom:15px;">
                                ⏳ بانتظار مضيف الغرفة لبدء جولة جديدة...
                            </div>
                        `}
                        <button onclick="leaveRoom()" style="background:var(--error); width:100%;">🚪 مغادرة الغرفة</button>
                    </div>`;
                return;
            }

            // 2. Play State View
            // Opponents list rendering
            let opponentsHTML = players.filter(p => p.user_id != currentUser.user_id).map(p => {
                const isOpponentTurn = gd.ordered_ids[gd.turn_index] == p.user_id;
                const oppHand = gd.hands[String(p.user_id)] || [];
                const hasOneCard = oppHand.length === 1;
                
                // Catcher logic: if opponent has 1 card and hasn't said uno, show catch button
                const canCatch = hasOneCard && !p.said_uno;

                return `
                    <div style="background:rgba(255,255,255,0.05); padding:12px; border-radius:15px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center; border: 1.5px solid ${isOpponentTurn ? 'var(--accent)' : 'transparent'};">
                        <div style="display:flex; flex-direction:column; text-align:right;">
                            <span style="font-weight:bold;">👤 ${p.player_name} ${isOpponentTurn ? '🟢 (دوره)' : ''}</span>
                            <span style="font-size:13px; color:#aaa;">الأوراق المتبقية: <b style="color:white;">${oppHand.length}</b></span>
                        </div>
                        <div style="display:flex; gap:8px;">
                            ${p.said_uno ? `<span style="background:rgba(255,118,117,0.2); color:#ff7675; padding:3px 8px; border-radius:8px; font-size:11px; font-weight:bold; animation:pulse 1s infinite;">🚨 أونو!</span>` : ''}
                            ${canCatch ? `<button onclick="catchUnoPlayer(${p.user_id})" style="background: linear-gradient(135deg, #e67e22, #d35400); margin:0; padding:5px 12px; font-size:12px; width:auto; font-weight:bold;">🪤 صيده!</button>` : ''}
                        </div>
                    </div>
                `;
            }).join('');

            // Rendering top discard card
            const topCard = gd.top_card;
            const currentColor = gd.current_color;
            let colorDisplay = "أسود";
            let colorDotHex = "#2d3436";
            if (currentColor === '🔴') { colorDisplay = "أحمر"; colorDotHex = "#d63031"; }
            else if (currentColor === '🔵') { colorDisplay = "أزرق"; colorDotHex = "#0984e3"; }
            else if (currentColor === '🟡') { colorDisplay = "أصفر"; colorDotHex = "#fdcb6e"; }
            else if (currentColor === '🟢') { colorDisplay = "أخضر"; colorDotHex = "#2ecc71"; }

            const topCardHTML = getUnoCardHTML(topCard, false, null);

            // My hand rendering
            let handHTML = myHand.map(card => {
                const isPlayable = isMyTurn && checkUnoValidityJS(card, topCard, currentColor);
                return getUnoCardHTML(card, isPlayable, `playUnoCard('${card.replace(/'/g, "\\'")}')`);
            }).join('');

            // Direction indicator
            const dirText = gd.direction === 1 ? "🔄 اتجاه اللعب: مع عقارب الساعة" : "🔄 اتجاه اللعب: عكس عقارب الساعة";

            document.getElementById('main-ui').innerHTML = `
                <div class="card domino-game-card" style="padding:15px; max-width:100%; width:98vw; min-height:85vh; display:flex; flex-direction:column; border-color:#ff7675;">
                    
                    <!-- الخصوم والاتجاه -->
                    <div style="margin-bottom:15px;">
                        <div style="font-size:12px; color:#aaa; margin-bottom:10px; text-align:center;">${dirText}</div>
                        ${opponentsHTML}
                    </div>

                    <!-- الساحة والورقة المكشوفة -->
                    <div style="flex-grow:1; background:rgba(0,0,0,0.3); border-radius:20px; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:20px; border:2px dashed rgba(255,255,255,0.1); margin-bottom:15px; min-height:180px;">
                        <div style="font-size:13px; color:#aaa; margin-bottom:8px;">الورقة المكشوفة حالياً</div>
                        <div style="margin-bottom:10px;">
                            ${topCardHTML}
                        </div>
                        <div style="font-size:14px; font-weight:bold; display:flex; align-items:center; justify-content:center;">
                            اللون الحالي: 
                            <span class="uno-color-dot" style="background:${colorDotHex}"></span> 
                            <span>${colorDisplay}</span>
                        </div>
                    </div>

                    <!-- إعلانات الدور وحالة أونو الخاصة بي -->
                    <div style="text-align:center; margin-bottom:10px;">
                        ${isMyTurn ? `
                            <div style="background:rgba(46,204,113,0.15); color:#2ecc71; padding:8px; border-radius:10px; font-weight:bold; font-size:15px; animation:pulse 1.5s infinite;">
                                👉 دورك الآن! العب ورقة أو اسحب.
                            </div>
                        ` : `
                            <div style="background:rgba(255,255,255,0.05); color:#ccc; padding:8px; border-radius:10px; font-size:14px;">
                                بانتظار دور الخصم: <b style="color:var(--accent);">${currentTurnPlayer ? currentTurnPlayer.player_name : ''}</b>
                            </div>
                        `}
                    </div>

                    <!-- لوحة التحكم والأوراق -->
                    <div style="background:rgba(0,0,0,0.2); padding:12px; border-radius:15px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; gap:10px;">
                            <div style="font-size:13px; color:#aaa;">أوراقك (${myHand.length})</div>
                            <div style="display:flex; gap:8px;">
                                ${isMyTurn ? `<button onclick="drawUnoCard()" style="background:#0984e3; margin:0; padding:6px 12px; font-size:13px; width:auto; font-weight:bold;">📥 سحب ورقة</button>` : ''}
                                ${myHand.length <= 2 ? `<button class="uno-neon-glow" onclick="sayUno()" style="background:#ff7675; color:white; margin:0; padding:6px 12px; font-size:13px; width:auto; font-weight:bold;">🚨 أونو!</button>` : ''}
                            </div>
                        </div>

                        <!-- الكروت يمين ليسار مع شريط التمرير -->
                        <div style="display:flex; overflow-x:auto; padding:10px 0; gap:8px; justify-content:flex-start; min-height:130px; box-sizing:border-box;">
                            ${handHTML}
                        </div>
                    </div>

                </div>`;
        }

        async function playUnoCard(card) {
            // Check if it is a wild card requiring color selection
            const isWild = card.includes("جوكر") || card.includes("🌈") || card.includes("🔥") || card.includes("💧") || card.includes("🌊");
            if (isWild) {
                selectUnoColor(card);
            } else {
                submitPlayUnoCard(card, null);
            }
        }

        function selectUnoColor(card) {
            const modal = document.createElement('div');
            modal.style = "position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.8); display:flex; justify-content:center; align-items:center; z-index:9999; backdrop-filter:blur(5px);";
            modal.innerHTML = `
                <div class="card" style="border-color: #ff7675; text-align:center; max-width:320px;">
                    <h3>اختر اللون الجديد 🌈</h3>
                    <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap:15px; margin:20px 0;">
                        <button class="uno-color-choice-btn" onclick="submitPlayUnoCard('${card.replace(/'/g, "\\'")}', '🔴')" style="background:#d63031; color:white; font-weight:bold;">🔴 أحمر</button>
                        <button class="uno-color-choice-btn" onclick="submitPlayUnoCard('${card.replace(/'/g, "\\'")}', '🔵')" style="background:#0984e3; color:white; font-weight:bold;">🔵 أزرق</button>
                        <button class="uno-color-choice-btn" onclick="submitPlayUnoCard('${card.replace(/'/g, "\\'")}', '🟡')" style="background:#fdcb6e; color:#2d3436; font-weight:bold;">🟡 أصفر</button>
                        <button class="uno-color-choice-btn" onclick="submitPlayUnoCard('${card.replace(/'/g, "\\'")}', '🟢')" style="background:#2ecc71; color:white; font-weight:bold;">🟢 أخضر</button>
                    </div>
                    <button onclick="this.parentElement.parentElement.remove()" style="background:#636e72; width:100%;">إلغاء</button>
                </div>
            `;
            document.body.appendChild(modal);
        }

        async function submitPlayUnoCard(card, chosenColor) {
            // Remove selection modal if open
            const modals = document.querySelectorAll('div[style*="z-index: 9999"]');
            modals.forEach(m => m.remove());

            try {
                const res = await fetch('/api/uno/play', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        room_code: currentRoom,
                        user_id: currentUser.user_id,
                        card: card,
                        chosen_color: chosenColor
                    })
                });
                const d = await res.json();
                if(!d.success) alert(d.msg || "حدث خطأ");
                else {
                    updateRoomState();
                }
            } catch(e) { console.error(e); }
        }

        async function drawUnoCard() {
            try {
                const res = await fetch('/api/uno/draw', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        room_code: currentRoom,
                        user_id: currentUser.user_id
                    })
                });
                const d = await res.json();
                if(!d.success) alert(d.msg || "حدث خطأ");
                else {
                    if (d.is_playable) {
                        // Let user choose to play the card they just drew
                        const playIt = confirm(`سحبت ورقة: ${d.card}\nهل تريد لعبها فوراً؟`);
                        if (playIt) {
                            playUnoCard(d.card);
                            return;
                        } else {
                            // If they choose not to play it, pass the turn manually
                            await passUnoTurn();
                        }
                    }
                    updateRoomState();
                }
            } catch(e) { console.error(e); }
        }

        async function passUnoTurn() {
            try {
                await fetch('/api/uno/pass', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        room_code: currentRoom,
                        user_id: currentUser.user_id
                    })
                });
            } catch(e) { console.error(e); }
        }

        async function sayUno() {
            try {
                const res = await fetch('/api/uno/say_uno', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        room_code: currentRoom,
                        user_id: currentUser.user_id
                    })
                });
                const d = await res.json();
                if(d.success) {
                    showToast("صحت أونو بنجاح! 🚨");
                    updateRoomState();
                } else {
                    alert(d.msg || "حدث خطأ");
                }
            } catch(e) { console.error(e); }
        }

        async function catchUnoPlayer(targetId) {
            try {
                const res = await fetch('/api/uno/catch', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        room_code: currentRoom,
                        user_id: currentUser.user_id,
                        target_id: targetId
                    })
                });
                const d = await res.json();
                if(d.success) {
                    showToast(d.msg);
                    updateRoomState();
                } else {
                    alert(d.msg || "حدث خطأ");
                }
            } catch(e) { console.error(e); }
        }

        init();
    </script>
</body>
</html>
"""
