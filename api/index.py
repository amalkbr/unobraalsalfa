import os
import logging
import random
import json
import base64
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# 1. التكوين الأساسي لـ Vercel - يجب أن يكون 'app' في مستوى علوي
app = FastAPI()

# إعداد السجلات
logging.basicConfig(level=logging.INFO)

# 2. منطق قاعدة البيانات مع معالجة الأخطاء لضمان عدم ظهور شاشة بيضاء
def get_db_conn():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        return None
    try:
        return psycopg2.connect(db_url, connect_timeout=5)
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        return None

def db_query(sql, params=(), commit=False):
    conn = get_db_conn()
    if not conn:
        return None
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(sql, params)
        if commit:
            conn.commit()
            return True
        return cur.fetchall()
    except Exception as e:
        logging.error(f"Query Error: {e}")
        return None
    finally:
        cur.close()
        conn.close()

# تهيئة الجداول عند أول طلب أو تشغيل
@app.on_event("startup")
async def startup_db():
    conn = get_db_conn()
    if conn:
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        player_name TEXT,
                        username_key VARCHAR(50) UNIQUE,
                        password_key VARCHAR(50),
                        avatar_url TEXT,
                        is_registered BOOLEAN DEFAULT FALSE)''')
        conn.commit()
        cur.close()
        conn.close()

# 3. بيانات اللعبة (برا السالفة)
CATEGORIES = {
    "ألعاب": ["ببجي", "فيفا", "ماينكرافت", "قراند", "فورتنايت", "كول اوف ديوتي", "روبلوكس", "فري فاير"],
    "حيوانات": ["أسد", "فيل", "زرافة", "نمر", "دب", "ثعلب", "حمار وحشي", "قطة", "كلب", "حصان"],
    "أكلات": ["بيتزا", "برجر", "شاورما", "منسف", "كبسة", "معكرونة", "كباب", "فلافل", "سوشي", "تاكو"],
    "كرة قدم": ["ميسي", "رونالدو", "صلاح", "نيمار", "مبابي", "هالاند", "بنزيمة", "مودريتش"],
    "سيارات": ["تويوتا", "مرسيدس", "بي ام دبليو", "تسلا", "فورد", "هوندا", "نيسان", "أودي"],
    "انمي": ["ون بيس", "ناروتو", "هجوم العمالقة", "ديث نوت", "دراغون بول", "هنتر x هنتر"],
    "مدن": ["الرياض", "دبي", "القاهرة", "عمان", "الكويت", "الدوحة", "بغداد", "المنامة", "مسقط", "القدس"]
}

# 4. الواجهة الأمامية (HTML) مدمجة في الـ Route الرئيسي
@app.get("/", response_class=HTMLResponse)
async def home():
    cat_json = json.dumps(list(CATEGORIES.keys()), ensure_ascii=False)
    return f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>برا السالفة</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; margin: 0; padding: 15px; text-align: center; direction: rtl; color: #333; }}
        .card {{ background: white; padding: 25px; border-radius: 20px; box-shadow: 0 8px 20px rgba(0,0,0,0.1); max-width: 450px; margin: 20px auto; }}
        input, select, button {{ width: 100%; padding: 14px; margin: 10px 0; border-radius: 12px; border: 1px solid #ddd; font-size: 16px; box-sizing: border-box; outline: none; }}
        button {{ background: #007bff; color: white; border: none; font-weight: bold; cursor: pointer; transition: 0.3s; }}
        button:active {{ transform: scale(0.95); }}
        .secondary {{ background: #28a745; }}
        .danger {{ background: #dc3545; }}
        .avatar-img {{ width: 90px; height: 90px; border-radius: 50%; object-fit: cover; border: 4px solid #007bff; margin-bottom: 10px; }}
        .word-display {{ font-size: 32px; font-weight: bold; color: #dc3545; padding: 30px; background: #fff0f0; border-radius: 20px; display: none; margin: 20px 0; border: 2px dashed #dc3545; }}
        .p-item {{ background: #f8f9fa; padding: 10px; border-radius: 10px; margin: 5px 0; display: flex; align-items: center; }}
    </style>
</head>
<body>
    <div id="app"><div class="card"><h1>جاري التحميل...</h1></div></div>

    <script>
        const cats = {cat_json};
        const state = {{
            user: JSON.parse(localStorage.getItem('user') || 'null'),
            view: 'auth',
            game: null
        }};

        function render() {{
            const appDiv = document.getElementById('app');
            if (!state.user) return renderAuth(appDiv);
            if (state.view === 'profile') return renderProfile(appDiv);
            if (state.view === 'offline') return renderOffline(appDiv);
            if (state.view === 'play') return renderPlay(appDiv);
            renderMain(appDiv);
        }}

        function renderAuth(app) {{
            app.innerHTML = `
                <div class="card">
                    <h2>برا السالفة - دخول</h2>
                    <input id="u" placeholder="اليوزر">
                    <input id="p" type="password" placeholder="كلمة المرور">
                    <button onclick="login()">دخول</button>
                    <hr>
                    <p>ليس لديك حساب؟ سجل أدناه:</p>
                    <input id="rn" placeholder="الاسم بالعربي">
                    <input id="ru" placeholder="يوزر جديد">
                    <input id="rp" type="password" placeholder="باسورد">
                    <button class="secondary" onclick="reg()">إنشاء حساب جديد</button>
                </div>`;
        }

        async function login() {{
            const res = await fetch('/api/login', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{username:document.getElementById('u').value, password:document.getElementById('p').value}})}});
            const d = await res.json();
            if(d.ok) {{ state.user=d.user; localStorage.setItem('user', JSON.stringify(d.user)); state.view='main'; render(); }} else alert(d.error);
        }}

        async function reg() {{
            const res = await fetch('/api/register', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{name:document.getElementById('rn').value, username:document.getElementById('ru').value, password:document.getElementById('rp').value}})}});
            const d = await res.json();
            if(d.ok) alert('تم التسجيل! يمكنك الآن تسجيل الدخول'); else alert(d.error);
        }}

        function renderMain(app) {{
            app.innerHTML = `
                <div class="card">
                    <img src="${{state.user.avatar || 'https://cdn-icons-png.flaticon.com/512/149/149071.png'}}" class="avatar-img" onclick="state.view='profile';render()">
                    <h3>مرحباً، ${{state.user.name}} 👋</h3>
                    <button class="secondary" style="padding:30px; font-size:20px" onclick="state.view='offline';render()">🎮 لعب أوفلاين</button>
                    <button class="danger" onclick="logout()">تسجيل خروج</button>
                </div>`;
        }

        function renderProfile(app) {{
            app.innerHTML = `
                <div class="card">
                    <h2>الملف الشخصي</h2>
                    <img src="${{state.user.avatar || 'https://cdn-icons-png.flaticon.com/512/149/149071.png'}}" class="avatar-img">
                    <p>تغيير الصورة الشخصية:</p>
                    <input type="file" onchange="up(this)" accept="image/*">
                    <button onclick="state.view='main';render()">العودة للرئيسية</button>
                </div>`;
        }

        async function up(input) {{
            const reader = new FileReader();
            reader.onload = async (e) => {{
                const res = await fetch('/api/update-avatar', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{user_id:state.user.id, image:e.target.result}})}});
                if((await res.json()).ok) {{ state.user.avatar=e.target.result; localStorage.setItem('user', JSON.stringify(state.user)); render(); }}
            }};
            reader.readAsDataURL(input.files[0]);
        }}

        function renderOffline(app) {{
            let options = cats.map(c => `<option>${{c}}</option>`).join('');
            app.innerHTML = `
                <div class="card">
                    <h2>إعداد اللعبة</h2>
                    <div id="ps">
                        <input class="pi" placeholder="لاعب 1">
                        <input class="pi" placeholder="لاعب 2">
                        <input class="pi" placeholder="لاعب 3">
                    </div>
                    <button class="warning" onclick="addP()">+ إضافة لاعب</button>
                    <label>اختر القسم:</label>
                    <select id="sc">${{options}}</select>
                    <button class="secondary" onclick="start()">ابدأ اللعب الآن</button>
                    <button class="danger" onclick="state.view='main';render()">رجوع</button>
                </div>`;
        }

        function addP() {{ const i=document.createElement('input'); i.className='pi'; i.placeholder='لاعب جديد'; document.getElementById('ps').appendChild(i); }}

        async function start() {{
            const players = Array.from(document.querySelectorAll('.pi')).map(i=>i.value).filter(v=>v);
            if(players.length < 3) return alert('يجب تواجد 3 لاعبين على الأقل');
            const res = await fetch('/api/start-offline', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{players, category:document.getElementById('sc').value}})}});
            state.game = await res.json(); state.view='play'; render();
        }}

        function renderPlay(app) {{
            const g = state.game;
            const p = g.players[g.idx];
            app.innerHTML = `
                <div class="card">
                    <h3>دور اللاعب: <span style="color:#007bff">${{p}}</span></h3>
                    <p>مرر الجهاز له ثم اضغط الزر</p>
                    <div id="wb" class="word-display"></div>
                    <button id="sb" onclick="show()">اكشف السالفة</button>
                    <button id="nb" style="display:none" onclick="next()">اللاعب التالي</button>
                </div>`;
        }

        function show() {{
            const g = state.game;
            const box = document.getElementById('wb');
            box.innerText = g.roles[g.idx] === 'spy' ? '🕵️ أنت برا السالفة!' : '🤫 السالفة هي: ' + g.word;
            box.style.display = 'block'; document.getElementById('sb').style.display='none'; document.getElementById('nb').style.display='block';
        }}

        function next() {{
            state.game.idx++;
            if(state.game.idx >= state.game.players.length) {{ alert('انتهى توزيع الأدوار! ابدأوا النقاش الآن'); state.view='main'; }}
            render();
        }}

        function logout() {{ localStorage.clear(); location.reload(); }}
        function id(i) {{ return document.getElementById(i); }}
        window.onload = render;
    </script>
</body>
</html>
    """

# 5. واجهات البرمجية (API)
class UserAuth(BaseModel):
    name: str = ""
    username: str
    password: str

@app.post("/api/register")
async def register(data: UserAuth):
    if len(data.username) < 3: return {"ok": False, "error": "اسم المستخدم قصير جداً"}
    uid = random.randint(1000, 999999)
    res = db_query("INSERT INTO users (user_id, player_name, username_key, password_key, is_registered) VALUES (%s, %s, %s, %s, TRUE)",
                   (uid, data.name, data.username, data.password), commit=True)
    if res: return {"ok": True}
    return {"ok": False, "error": "اليوزر مأخوذ أو حدث خطأ في القاعدة"}

@app.post("/api/login")
async def login(data: UserAuth):
    u = db_query("SELECT user_id, player_name, avatar_url FROM users WHERE username_key=%s AND password_key=%s", (data.username, data.password))
    if u:
        return {"ok": True, "user": {"id": u[0]['user_id'], "name": u[0]['player_name'], "avatar": u[0]['avatar_url']}}
    return {"ok": False, "error": "اسم المستخدم أو كلمة المرور خطأ"}

class Avatar(BaseModel):
    user_id: int
    image: str

@app.post("/api/update-avatar")
async def update_avatar(data: Avatar):
    res = db_query("UPDATE users SET avatar_url=%s WHERE user_id=%s", (data.image, data.user_id), commit=True)
    return {"ok": True if res else False}

class GameStart(BaseModel):
    players: list
    category: str

@app.post("/api/start-offline")
async def start_game(data: GameStart):
    word = random.choice(CATEGORIES.get(data.category, ["خطأ"]))
    roles = ["in"] * len(data.players)
    roles[random.randint(0, len(data.players)-1)] = "spy"
    return {"players": data.players, "word": word, "roles": roles, "idx": 0}
