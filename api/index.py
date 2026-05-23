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

# --- Database Logic Integrated ---
def get_db_conn():
    db_url = os.environ.get('DATABASE_URL')
    return psycopg2.connect(db_url)

def db_query(sql, params=(), commit=False):
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(sql, params)
        if commit:
            conn.commit()
            return True
        return cur.fetchall()
    except Exception as e:
        logging.error(f"DB Error: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def init_db():
    conn = get_db_conn()
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

# --- FastAPI App ---
app = FastAPI()

@app.on_event("startup")
async def startup():
    try:
        init_db()
    except Exception as e:
        logging.error(f"Startup DB Error: {e}")

CATEGORIES = {
    "ألعاب": ["ببجي", "فيفا", "ماينكرافت", "قراند", "فورتنايت", "كول اوف ديوتي", "روبلوكس", "فري فاير"],
    "حيوانات": ["أسد", "فيل", "زرافة", "نمر", "دب", "ثعلب", "حمار وحشي", "قطة", "كلب", "حصان"],
    "أكلات": ["بيتزا", "برجر", "شاورما", "منسف", "كبسة", "معكرونة", "كباب", "فلافل", "سوشي", "تاكو"],
    "كرة قدم": ["ميسي", "رونالدو", "صلاح", "نيمار", "مبابي", "هالاند", "بنزيمة", "مودريتش"],
    "سيارات": ["تويوتا", "مرسيدس", "بي ام دبليو", "تسلا", "فورد", "هوندا", "نيسان", "أودي"],
    "انمي": ["ون بيس", "ناروتو", "هجوم العمالقة", "ديث نوت", "دراغون بول", "هنتر x هنتر"],
    "مدن": ["الرياض", "دبي", "القاهرة", "عمان", "الكويت", "الدوحة", "بغداد", "المنامة", "مسقط", "القدس"]
}

@app.get("/", response_class=HTMLResponse)
async def get_index():
    cat_json = json.dumps(list(CATEGORIES.keys()), ensure_ascii=False)
    return f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>برا السالفة</title>
    <style>
        body {{ font-family: sans-serif; background: #f0f2f5; margin: 0; padding: 15px; text-align: center; direction: rtl; }}
        .card {{ background: white; padding: 20px; border-radius: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); max-width: 450px; margin: auto; }}
        input, select, button {{ width: 100%; padding: 12px; margin: 8px 0; border-radius: 10px; border: 1px solid #ddd; font-size: 16px; box-sizing: border-box; }}
        button {{ background: #007bff; color: white; border: none; font-weight: bold; cursor: pointer; }}
        .secondary {{ background: #28a745; }}
        .danger {{ background: #dc3545; }}
        .avatar-img {{ width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 3px solid #007bff; }}
        .word-display {{ font-size: 28px; font-weight: bold; color: #dc3545; padding: 20px; background: #fff0f0; border-radius: 15px; display: none; margin: 15px 0; }}
    </style>
</head>
<body>
    <div id="app"></div>
    <script>
        const cats = {cat_json};
        const state = {{
            user: JSON.parse(localStorage.getItem('user') || 'null'),
            view: 'auth',
            game: null
        }};

        function render() {{
            const app = document.getElementById('app');
            if (!state.user) return renderAuth(app);
            if (state.view === 'main') return renderMain(app);
            if (state.view === 'profile') return renderProfile(app);
            if (state.view === 'offline') return renderOffline(app);
            if (state.view === 'play') return renderPlay(app);
            renderMain(app);
        }}

        function renderAuth(app) {{
            app.innerHTML = `
                <div class="card">
                    <h2>تسجيل الدخول</h2>
                    <input id="u" placeholder="اليوزر">
                    <input id="p" type="password" placeholder="كلمة المرور">
                    <button onclick="login()">دخول</button>
                    <hr>
                    <input id="rn" placeholder="الاسم بالعربي">
                    <input id="ru" placeholder="يوزر جديد">
                    <input id="rp" type="password" placeholder="باسورد">
                    <button class="secondary" onclick="reg()">إنشاء حساب</button>
                </div>`;
        }

        async function login() {{
            const res = await fetch('/api/login', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{username:id('u').value, password:id('p').value}})}});
            const d = await res.json();
            if(d.ok) {{ state.user=d.user; localStorage.setItem('user', JSON.stringify(d.user)); state.view='main'; render(); }} else alert(d.error);
        }}

        async function reg() {{
            const res = await fetch('/api/register', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{name:id('rn').value, username:id('ru').value, password:id('rp').value}})}});
            const d = await res.json();
            if(d.ok) alert('تم! سجل دخولك'); else alert(d.error);
        }}

        function renderMain(app) {{
            app.innerHTML = `
                <div class="card">
                    <img src="${{state.user.avatar || 'https://via.placeholder.com/80'}}" class="avatar-img" onclick="state.view='profile';render()">
                    <h3>هلا ${{state.user.name}}</h3>
                    <button class="secondary" style="padding:25px" onclick="state.view='offline';render()">لعب أوفلاين</button>
                    <button class="danger" onclick="logout()">خروج</button>
                </div>`;
        }

        function renderProfile(app) {{
            app.innerHTML = `
                <div class="card">
                    <h2>الملف الشخصي</h2>
                    <img src="${{state.user.avatar || 'https://via.placeholder.com/80'}}" class="avatar-img">
                    <input type="file" onchange="up(this)" accept="image/*">
                    <button onclick="state.view='main';render()">رجوع</button>
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
                    <div id="ps"><input class="pi" placeholder="لاعب 1"><input class="pi" placeholder="لاعب 2"><input class="pi" placeholder="لاعب 3"></div>
                    <button onclick="addP()">+ لاعب</button>
                    <select id="sc">${{options}}</select>
                    <button class="secondary" onclick="start()">ابدأ</button>
                    <button class="danger" onclick="state.view='main';render()">رجوع</button>
                </div>`;
        }

        function addP() {{ const i=document.createElement('input'); i.className='pi'; i.placeholder='لاعب جديد'; id('ps').appendChild(i); }}

        async function start() {{
            const players = Array.from(document.querySelectorAll('.pi')).map(i=>i.value).filter(v=>v);
            if(players.length < 3) return alert('3 لاعبين عالأقل');
            const res = await fetch('/api/start-offline', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{players, category:id('sc').value}})}});
            state.game = await res.json(); state.view='play'; render();
        }}

        function renderPlay(app) {{
            const g = state.game;
            const p = g.players[g.idx];
            app.innerHTML = `
                <div class="card">
                    <h3>دور: ${{p}}</h3>
                    <div id="wb" class="word-display"></div>
                    <button id="sb" onclick="show()">اكشف السالفة</button>
                    <button id="nb" style="display:none" onclick="next()">التالي</button>
                </div>`;
        }

        function show() {{
            const g = state.game;
            const box = id('wb');
            box.innerText = g.roles[g.idx] === 'spy' ? 'أنت برا السالفة!' : g.word;
            box.style.display = 'block'; id('sb').style.display='none'; id('nb').style.display='block';
        }}

        function next() {{
            state.game.idx++;
            if(state.game.idx >= state.game.players.length) {{ alert('ابدأوا النقاش!'); state.view='main'; }}
            render();
        }}

        function logout() {{ localStorage.clear(); location.reload(); }}
        const id = i => document.getElementById(i);
        window.onload = render;
    </script>
</body>
</html>
    """

# API Models
class UserAuth(BaseModel):
    name: str = ""
    username: str
    password: str

@app.post("/api/register")
async def register(data: UserAuth):
    if len(data.username) < 3: return {"ok": False, "error": "اليوزر قصير"}
    uid = random.randint(1000, 999999)
    res = db_query("INSERT INTO users (user_id, player_name, username_key, password_key, is_registered) VALUES (%s, %s, %s, %s, TRUE)",
                   (uid, data.name, data.username, data.password), commit=True)
    return {"ok": True} if res else {"ok": False, "error": "اليوزر مأخوذ"}

@app.post("/api/login")
async def login(data: UserAuth):
    u = db_query("SELECT user_id, player_name, avatar_url FROM users WHERE username_key=%s AND password_key=%s", (data.username, data.password))
    if u: return {"ok": True, "user": {"id": u[0]['user_id'], "name": u[0]['player_name'], "avatar": u[0]['avatar_url']}}
    return {"ok": False, "error": "خطأ في البيانات"}

class Avatar(BaseModel):
    user_id: int
    image: str

@app.post("/api/update-avatar")
async def update_avatar(data: Avatar):
    db_query("UPDATE users SET avatar_url=%s WHERE user_id=%s", (data.image, data.user_id), commit=True)
    return {"ok": True}

class GameStart(BaseModel):
    players: list
    category: str

@app.post("/api/start-offline")
async def start_game(data: GameStart):
    word = random.choice(CATEGORIES.get(data.category, ["خطأ"]))
    roles = ["in"] * len(data.players)
    roles[random.randint(0, len(data.players)-1)] = "spy"
    return {"players": data.players, "word": word, "roles": roles, "idx": 0}
