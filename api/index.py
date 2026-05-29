import os
import sys
import json
import random
import string
import time
import base64
import psycopg2
from fastapi import FastAPI, Request, Response, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse

# 1. إعداد المسارات فوراً
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# 2. تعريف التطبيق بأكثر من اسم لضمان اكتشافه بواسطة Vercel
app = FastAPI()
handler = app
application = app

# 3. تعريف دوال احتياطية لتجنب الانهيار في حال فشل الاستيراد
def get_db_fallback():
    class DummyContext:
        def __enter__(self): return None
        def __exit__(self, *args): pass
    return DummyContext()

get_db = get_db_fallback
RealDictCursor = None
get_db_conn = lambda: None

domino_router = APIRouter()
spy_router = APIRouter()

# 4. استيراد الموديلات بحذر
try:
    from database import get_db as db, RealDictCursor as rdc, get_db_conn as gdc
    from domino import router as dr
    from spy import router as sr
    get_db, RealDictCursor, get_db_conn = db, rdc, gdc
    domino_router, spy_router = dr, sr
except Exception as e:
    print(f"Import Error: {e}")

app.include_router(domino_router)
app.include_router(spy_router)

# --- البيانات الأساسية ---
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
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, username_key TEXT UNIQUE, password_key TEXT, player_name TEXT, is_registered BOOLEAN DEFAULT FALSE, total_wins INTEGER DEFAULT 0, online_points INTEGER DEFAULT 0, saved_players JSONB DEFAULT '[]' );
                    CREATE TABLE IF NOT EXISTS rooms (room_code TEXT PRIMARY KEY, host_id BIGINT, status TEXT DEFAULT 'waiting', category TEXT, win_limit INTEGER DEFAULT 5, current_turn_asker BIGINT, current_turn_answerer BIGINT, secret_word TEXT, spy_id BIGINT, game_data JSONB DEFAULT '{}', game_type TEXT DEFAULT 'spy', max_players INTEGER DEFAULT 10, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP );
                    CREATE TABLE IF NOT EXISTS room_players (room_code TEXT, user_id BIGINT, player_name TEXT, score INTEGER DEFAULT 0, is_ready BOOLEAN DEFAULT FALSE, yellow_cards INTEGER DEFAULT 0, red_card BOOLEAN DEFAULT FALSE, vote_limit INTEGER, vote_cat TEXT, join_order INTEGER DEFAULT 0, team TEXT, PRIMARY KEY (room_code, user_id) );
                    CREATE TABLE IF NOT EXISTS categories (id SERIAL PRIMARY KEY, name TEXT UNIQUE, image_url TEXT, display_order INTEGER DEFAULT 0 );
                    CREATE TABLE IF NOT EXISTS words (id SERIAL PRIMARY KEY, category TEXT, word TEXT );
                    CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT );
                    CREATE TABLE IF NOT EXISTS feedback (id SERIAL PRIMARY KEY, user_id BIGINT, player_name TEXT, message TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP );
                    CREATE TABLE IF NOT EXISTS announcements (id SERIAL PRIMARY KEY, text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
                """)
                # Migrations
                migrations = [
                    "ALTER TABLE feedback ADD COLUMN IF NOT EXISTS announcement_id INTEGER",
                    "ALTER TABLE feedback ADD COLUMN IF NOT EXISTS text TEXT",
                    "ALTER TABLE feedback ADD COLUMN IF NOT EXISTS type TEXT",
                    "ALTER TABLE feedback ADD COLUMN IF NOT EXISTS original_text TEXT"
                ]
                for m in migrations:
                    try: cur.execute(m); conn.commit()
                    except: conn.rollback()
                conn.commit()
                DB_INITIALIZED = True
        except Exception as e:
            print(f"DB Init Error: {e}")

try:
    init_db()
except:
    pass

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(content=HTML_TEMPLATE)

@app.get("/manifest.json")
async def manifest():
    v = int(time.time())
    return {
        "name": "أونو وبرا السالفة",
        "short_name": "السالفة",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f0c29",
        "theme_color": "#6c5ce7",
        "icons": [{ "src": f"/api/app_icon.png?v={v}", "sizes": "512x512", "type": "image/png" }]
    }

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
                    return Response(content=base64.b64decode(row[0]), media_type="image/png")
        finally: conn.close()
    return RedirectResponse(url=default_icon)

@app.get("/api/admin/feedback")
async def get_feedback():
    with get_db() as conn:
        if not conn: return []
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM feedback ORDER BY created_at DESC LIMIT 100")
            return cur.fetchall()

@app.post("/api/feedback/delete")
async def delete_feedback(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False}
        with conn.cursor() as cur:
            cur.execute("DELETE FROM feedback WHERE id = %s", (data['id'],))
            conn.commit()
        return {"success": True}

@app.post("/api/feedback")
async def post_feedback(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False}
        with conn.cursor() as cur:
            cur.execute("INSERT INTO feedback (user_id, player_name, message) VALUES (%s, %s, %s)",
                        (data.get('user_id'), data.get('player_name', 'Unknown'), data.get('message', '').strip()))
            conn.commit()
        return {"success": True}

HTML_TEMPLATE = \"\"\"
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>أونو وبرا السالفة</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #00d2ff; --bg: #050505; --card: rgba(25, 25, 35, 0.95); --accent: #00ff88; --error: #ff2d55; }
        body { font-family: 'Cairo', sans-serif; background: #050505; color: white; margin: 0; }
        .card { background: var(--card); padding: 20px; border-radius: 20px; margin: 20px auto; max-width: 500px; border: 1px solid rgba(0,210,255,0.3); }
        button { background: var(--primary); color: white; border: none; padding: 10px 20px; border-radius: 10px; cursor: pointer; width: 100%; font-weight: bold; margin-top: 10px; }
        .admin-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .item-card { background: rgba(255,255,255,0.05); padding: 10px; border-radius: 10px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div id="main-ui">
        <div class="card">
            <h1>أونو وبرا السالفة</h1>
            <button onclick="showAdmin()">🛠️ الإدارة</button>
        </div>
    </div>
    <script>
        function escapeHtml(t) { return t.replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
        function showAdmin() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>لوحة التحكم</h2>
                    <button onclick="manageFeedback()">💬 الآراء</button>
                    <button onclick="location.reload()">🏠 الرئيسية</button>
                </div>`;
        }
        async function manageFeedback() {
            const res = await fetch('/api/admin/feedback');
            const data = await res.json();
            let h = '<h2>الآراء</h2>';
            data.forEach(f => {
                h += `<div class="item-card">
                    <b>${escapeHtml(f.player_name || '؟')}</b>
                    <p>${escapeHtml(f.message || f.text || '')}</p>
                    <button onclick="delFb(${f.id})" style="background:var(--error); width:auto;">حذف</button>
                </div>`;
            });
            h += '<button onclick="showAdmin()">رجوع</button>';
            document.getElementById('main-ui').innerHTML = `<div class="card">${h}</div>`;
        }
        async function delFb(id) {
            if(confirm('حذف؟')) {
                await fetch('/api/feedback/delete', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({id})});
                manageFeedback();
            }
        }
    </script>
</body>
</html>
\"\"\"
