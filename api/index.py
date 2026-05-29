import os
import sys
import json
import random
import string
import time
import base64
import psycopg2
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse

# إضافة المسارات لضمان اكتشاف الموديولات في Vercel
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# 1. تعريف التطبيق - يجب أن يكون في أعلى مستوى ممكن
app = FastAPI()

# 2. الاستيراد باستخدام المسارات المحلية (بفضل sys.path)
try:
    from database import get_db, RealDictCursor, get_db_conn
    from domino import router as domino_router
    from spy import router as spy_router
except (ImportError, ModuleNotFoundError):
    try:
        from api.database import get_db, RealDictCursor, get_db_conn
        from api.domino import router as domino_router
        from api.spy import router as spy_router
    except Exception as e:
        print(f"Critical Import Error: {e}")

app.include_router(domino_router)
app.include_router(spy_router)

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
    with get_db() as conn:
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
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    player_name TEXT,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

                # 2. هجرة البيانات وتوافق الأعمدة (Migrations)
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
                    "ALTER TABLE rooms ALTER COLUMN room_id TYPE TEXT USING room_id::TEXT",
                    "ALTER TABLE rooms ALTER COLUMN room_code TYPE TEXT USING room_code::TEXT",
                    "ALTER TABLE room_players ALTER COLUMN room_id TYPE TEXT USING room_id::TEXT",
                    "ALTER TABLE room_players ALTER COLUMN room_code TYPE TEXT USING room_code::TEXT",
                    "UPDATE rooms SET room_code = room_id WHERE room_code IS NULL AND room_id IS NOT NULL",
                    "UPDATE rooms SET room_id = room_code WHERE room_id IS NULL AND room_code IS NOT NULL",
                    "UPDATE rooms SET host_id = creator_id WHERE host_id IS NULL AND creator_id IS NOT NULL",
                    "UPDATE rooms SET creator_id = host_id WHERE creator_id IS NULL AND host_id IS NOT NULL",
                    "UPDATE room_players SET room_code = room_id WHERE room_code IS NULL AND room_id IS NOT NULL",
                    "UPDATE room_players SET room_id = room_code WHERE room_id IS NULL AND room_code IS NOT NULL",
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_rooms_room_code ON rooms(room_code)",
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_room_players_code_user ON room_players(room_code, user_id)",
                    "CREATE TABLE IF NOT EXISTS announcements (id SERIAL PRIMARY KEY, text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
                    "CREATE TABLE IF NOT EXISTS feedback (id SERIAL PRIMARY KEY, announcement_id INTEGER REFERENCES announcements(id) ON DELETE CASCADE, user_id BIGINT, player_name TEXT, text TEXT, type TEXT, original_text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
                    "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS game_type TEXT DEFAULT 'spy'",
                    "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS max_players INTEGER DEFAULT 10",
                    "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS room_code TEXT",
                    "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS host_id BIGINT",
                    "ALTER TABLE room_players ADD COLUMN IF NOT EXISTS team TEXT",
                    "ALTER TABLE room_players ADD COLUMN IF NOT EXISTS room_code TEXT"
                ]

                for step in migration_steps:
                    try:
                        cur.execute(step)
                        conn.commit()
                    except:
                        conn.rollback()

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

init_db()

@app.get("/", response_class=HTMLResponse)
async def home():
    response = HTMLResponse(content=HTML_TEMPLATE)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.get("/manifest.json")
async def manifest():
    import time
    version = int(time.time())
    icon_url = f"/api/app_icon.png?v={version}"
    manifest_data = {
        "name": "أونو وبرا السالفة",
        "short_name": "السالفة",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f0c29",
        "theme_color": "#6c5ce7",
        "icons": [{ "src": icon_url, "sizes": "512x512", "type": "image/png" }]
    }
    return JSONResponse(content=manifest_data)

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
                    img_data = base64.b64decode(row[0])
                    return Response(content=img_data, media_type="image/png")
        finally: conn.close()
    return RedirectResponse(url=default_icon)

@app.post("/api/admin/upload_icon")
async def upload_icon(request: Request):
    form = await request.form()
    file = form.get("icon")
    if not file: return {"success": False, "msg": "لم يتم اختيار ملف"}
    contents = await file.read()
    encoded = base64.b64encode(contents).decode('utf-8')
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO settings (key, value) VALUES ('app_icon_data', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (encoded,))
            conn.commit()
        return {"success": True}
    finally: conn.close()

@app.get("/api/announcements")
async def get_announcements():
    with get_db() as conn:
        if not conn: return []
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM announcements ORDER BY created_at DESC LIMIT 5")
                anns = cur.fetchall()
                for ann in anns:
                    cur.execute("SELECT * FROM feedback WHERE announcement_id = %s ORDER BY created_at DESC", (ann['id'],))
                    ann['feedback'] = cur.fetchall()
                return anns
        except: return []

@app.post("/api/admin/announcements/add")
async def add_announcement(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False}
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO announcements (text) VALUES (%s)", (data['text'],))
                conn.commit()
            return {"success": True}
        except: return {"success": False}

@app.post("/api/admin/announcements/update")
async def update_announcement(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False}
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE announcements SET text = %s WHERE id = %s", (data['text'], data['id']))
                conn.commit()
            return {"success": True}
        except: return {"success": False}

@app.post("/api/admin/announcements/delete")
async def delete_announcement(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False}
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM announcements WHERE id = %s", (data['id'],))
                conn.commit()
            return {"success": True}
        except: return {"success": False}

@app.post("/api/feedback/add")
async def add_feedback(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False}
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO feedback (announcement_id, user_id, player_name, text, type) VALUES (%s, %s, %s, %s, %s)",
                            (data.get('announcement_id'), data.get('user_id'), data.get('player_name'), data['text'], data.get('type')))
                conn.commit()
            return {"success": True}
        except: return {"success": False}

@app.post("/api/feedback/update")
async def update_feedback(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False}
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT type, text, original_text FROM feedback WHERE id = %s", (data['id'],))
                row = cur.fetchone()
                if row:
                    fb_type, current_text, orig = row
                    if fb_type != 'suggestion' and not orig:
                        cur.execute("UPDATE feedback SET text = %s, original_text = %s WHERE id = %s", (data['text'], current_text, data['id']))
                    else:
                        cur.execute("UPDATE feedback SET text = %s WHERE id = %s", (data['text'], data['id']))
                    conn.commit()
            return {"success": True}
        except: return {"success": False}

@app.post("/api/feedback/delete")
async def delete_feedback(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False}
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM feedback WHERE id = %s", (data['id'],))
                conn.commit()
            return {"success": True}
        except: return {"success": False}

@app.post("/api/feedback")
async def post_feedback(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False}
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO feedback (user_id, player_name, message) VALUES (%s, %s, %s)",
                            (data.get('user_id'), data.get('player_name', 'Unknown'), data.get('message', '').strip()))
                conn.commit()
            return {"success": True}
        except: return {"success": False}

@app.get("/api/admin/feedback")
async def get_feedback():
    with get_db() as conn:
        if not conn: return []
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM feedback ORDER BY created_at DESC LIMIT 100")
                return cur.fetchall()
        except: return []

@app.post("/api/admin/add_word")
async def add_word(data: dict):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            category = data.get('category')
            words = [w.strip() for w in data.get('word', '').split('\n') if w.strip()]
            for w in words:
                cur.execute("INSERT INTO words (category, word) VALUES (%s, %s)", (category, w))
            conn.commit()
        return {"success": True, "added_count": len(words)}
    finally: conn.close()

@app.get("/api/admin/words")
async def get_words():
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM words ORDER BY category, word")
            return cur.fetchall()
    finally: conn.close()

@app.get("/api/online/rankings")
async def get_online_rankings():
    with get_db() as conn:
        if not conn: return []
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT player_name, online_points FROM users WHERE online_points > 0 ORDER BY online_points DESC LIMIT 50")
                return cur.fetchall()
        except: return []

@app.get("/api/admin/players")
async def admin_get_players():
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT user_id, username_key, player_name, total_wins FROM users ORDER BY total_wins DESC LIMIT 200")
            return cur.fetchall()
    finally: conn.close()

@app.get("/api/categories")
async def get_categories():
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name, image_url, display_order FROM categories ORDER BY display_order ASC, name ASC")
            cats = cur.fetchall()
            return cats
    finally: conn.close()

@app.post("/api/admin/category/add")
async def add_category(data: dict):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO categories (name, image_url, display_order) VALUES (%s, %s, %s)",
                        (data['name'], data.get('image_url'), data.get('display_order', 0)))
            conn.commit()
        return {"success": True}
    finally: conn.close()

@app.post("/api/admin/category/update")
async def update_category(data: dict):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            if 'old_name' in data and data['old_name'] != data['name']:
                cur.execute("UPDATE words SET category = %s WHERE category = %s", (data['name'], data['old_name']))
            cur.execute("UPDATE categories SET name = %s, image_url = %s, display_order = %s WHERE id = %s",
                        (data['name'], data.get('image_url'), data.get('display_order', 0), data['id']))
            conn.commit()
        return {"success": True}
    finally: conn.close()

@app.post("/api/admin/category/delete")
async def delete_category(data: dict):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM categories WHERE id = %s", (data['id'],))
            conn.commit()
        return {"success": True}
    finally: conn.close()

@app.post("/api/admin/word/update")
async def update_word(data: dict):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE words SET word = %s WHERE id = %s", (data['word'], data['id']))
            conn.commit()
        return {"success": True}
    finally: conn.close()

@app.post("/api/admin/word/delete")
async def delete_word(data: dict):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM words WHERE id = %s", (data['id'],))
            conn.commit()
        return {"success": True}
    finally: conn.close()

@app.post("/api/user/save_players")
async def save_players(data: dict):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET saved_players = %s WHERE user_id = %s", (json.dumps(data['players']), int(data['user_id'])))
            conn.commit()
        return {"success": True}
    finally: conn.close()

@app.post("/api/game/report_winner")
async def report_winner(data: dict):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET total_wins = total_wins + 1 WHERE player_name = %s", (data['player_name'],))
            conn.commit()
        return {"success": True}
    finally: conn.close()

HTML_TEMPLATE = \"\"\"
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>أونو وبرا السالفة</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #00d2ff; --bg: #050505; --card: rgba(25, 25, 35, 0.95); --accent: #00ff88; --error: #ff2d55; --success: #00ff88; }
        body { font-family: 'Cairo', sans-serif; background: radial-gradient(circle at center, #1a1a2e 0%, #050505 100%); color: white; margin: 0; direction: rtl; }
        .card { background: var(--card); padding: 20px; border-radius: 28px; box-shadow: 0 0 30px rgba(0, 210, 255, 0.2); border: 1px solid rgba(0, 210, 255, 0.4); max-width: 500px; margin: 20px auto; }
        button { background: var(--primary); color: white; border: none; padding: 12px 25px; border-radius: 15px; cursor: pointer; font-weight: bold; width: 100%; margin-top: 10px; }
        .admin-wide-card { max-width: 1000px; }
        .admin-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .admin-item-card { background: rgba(255,255,255,0.05); padding: 15px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); cursor: pointer; }
    </style>
</head>
<body>
    <div id="main-ui">
        <div class="card">
            <h1>جاري التحميل...</h1>
        </div>
    </div>

    <script>
        // دالة الهروب من HTML
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        async function navigateTo(screen) {
            if(screen === 'menu') showMenu();
            // ... بقية التنقل
        }

        function showMenu() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h1>القائمة الرئيسية</h1>
                    <button onclick="showAdminDashboard()">🛠️ لوحة الإدارة</button>
                </div>`;
        }

        async function showAdminDashboard(push = true) {
            document.getElementById('main-ui').innerHTML = `
                <div class="card admin-wide-card">
                    <h2>🛠️ لوحة التحكم الإدارية</h2>
                    <div class="admin-grid">
                        <div class="admin-item-card" onclick="adminManagePlayers()">👥 إدارة اللاعبين</div>
                        <div class="admin-item-card" onclick="adminManageCategories()">📂 الفئات والكلمات</div>
                        <div class="admin-item-card" onclick="adminManageFeedback()">💬 آراء المستخدمين</div>
                    </div>
                    <button onclick="showMenu()">🏠 القائمة الرئيسية</button>
                </div>`;
        }

        async function adminManageFeedback() {
            try {
                const res = await fetch('/api/admin/feedback');
                const feedback = await res.json();
                let h = '<h2>💬 آراء اللاعبين</h2><div style="max-height:60vh; overflow-y:auto;">';
                feedback.forEach(f => {
                    const date = new Date(f.created_at).toLocaleString('ar-EG');
                    h += `<div class="admin-item-card" style="margin-bottom:10px; border-left: 4px solid var(--primary);">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <b>${escapeHtml(f.player_name || 'غير معروف')}</b>
                            <small style="opacity:0.6;">${date}</small>
                        </div>
                        <p style="margin: 10px 0;">${escapeHtml(f.message || f.text || '')}</p>
                        <div style="display:flex; gap:10px;">
                             <button onclick="deleteFeedback(${f.id})" style="padding:5px; background:var(--error); font-size:12px; width:auto;">حذف</button>
                        </div>
                    </div>`;
                });
                h += '</div><button onclick="showAdminDashboard(false)">رجوع</button>';
                document.getElementById('main-ui').innerHTML = `<div class="card admin-wide-card">${h}</div>`;
            } catch(e) { alert("خطأ في التحميل"); }
        }

        async function deleteFeedback(id) {
            if(!confirm('هل أنت متأكد من حذف هذا الرأي؟')) return;
            try {
                const res = await fetch('/api/feedback/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id})
                });
                if((await res.json()).success) adminManageFeedback();
            } catch(e) { alert("فشل الحذف"); }
        }

        function renderDominoUI(room, players, userId) {
            const gd = room.game_data;
            if (gd.phase === 'round_end') {
                const title = gd.is_stalemate ? '🔒 قفلة! (تعادل فني)' : '🏁 نهاية الجولة';
                const winnerText = gd.round_winner_team === "0" ? 'الفريق أ فاز!' :
                                 gd.round_winner_team === "1" ? 'الفريق ب فاز!' : 'تعادل كامل!';

                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2>${title}</h2>
                        <h3 style="color: var(--accent)">${winnerText}</h3>
                        <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 15px; margin: 15px 0;">
                            <p>نقاط الجولة: ${gd.round_points || 0}</p>
                            <hr style="opacity: 0.2">
                            <p>الفريق أ: ${gd.scores["0"]}</p>
                            <p>الفريق ب: ${gd.scores["1"]}</p>
                        </div>
                        ${room.host_id == userId ? '<button onclick="dominoNextRound()">جولة جديدة</button>' : '<p>انتظار المضيف لبدء الجولة التالية...</p>'}
                    </div>
                `;
                return;
            }
            // ... (بقية واجهة الدومينو)
        }

        function init() { showMenu(); }
        init();
    </script>
</body>
</html>
\"\"\"
