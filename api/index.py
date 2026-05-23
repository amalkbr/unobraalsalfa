from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
import json
import random
import os
import base64
from typing import Optional

# Core FastAPI app - MUST be at the top level
app = FastAPI()

# Database helper (Lazy loading to prevent Vercel boot errors)
def get_db_conn():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        return None
    try:
        return psycopg2.connect(db_url, sslmode='require')
    except:
        return None

def db_query(sql, params=(), commit=False):
    conn = get_db_conn()
    if not conn: return None
    try:
        cur = conn.cursor(cursor_factory=__import__('psycopg2.extras').extras.RealDictCursor)
        cur.execute(sql, params)
        if commit:
            conn.commit()
            return True
        return cur.fetchall()
    except Exception as e:
        print(f"DB Error: {e}")
        return None
    finally:
        conn.close()

# Game Data
CATEGORIES = {
    "ألعاب": ["ببجي", "فيفا", "ماينكرافت", "قراند", "فورتنايت"],
    "حيوانات": ["أسد", "فيل", "زرافة", "نمر", "دب"],
    "أكلات": ["بيتزا", "برجر", "شاورما", "منسف", "كبسة"],
    "كرة قدم": ["ميسي", "رونالدو", "صلاح", "نيمار", "مبابي"]
}

@app.get("/", response_class=HTMLResponse)
async def home():
    cat_json = json.dumps(list(CATEGORIES.keys()), ensure_ascii=False)
    return f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>برا السالفة | Bara Alsalfa</title>
    <style>
        :root {{ --primary: #6c5ce7; --secondary: #a29bfe; --bg: #f9f9fb; --text: #2d3436; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); color: var(--text); text-align: center; padding: 20px; direction: rtl; margin: 0; }}
        .container {{ max-width: 500px; margin: auto; padding: 10px; }}
        .card {{ background: white; padding: 30px; border-radius: 24px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #eee; }}
        h1 {{ color: var(--primary); font-size: 2.5rem; margin-bottom: 10px; }}
        button {{ width: 100%; padding: 16px; margin: 12px 0; border-radius: 16px; border: none; background: var(--primary); color: white; font-weight: bold; font-size: 1.1rem; cursor: pointer; transition: 0.3s; }}
        button:active {{ transform: scale(0.98); }}
        .btn-outline {{ background: white; color: var(--primary); border: 2px solid var(--primary); }}
        .avatar-box {{ width: 80px; height: 80px; background: #eee; border-radius: 50%; margin: 0 auto 15px; overflow: hidden; display: flex; align-items: center; justify-content: center; }}
        .avatar-img {{ width: 100%; height: 100%; object-fit: cover; }}
        input {{ width: 100%; padding: 14px; margin: 10px 0; border-radius: 12px; border: 2px solid #eee; box-sizing: border-box; font-size: 1rem; text-align: center; }}
        input:focus {{ border-color: var(--primary); outline: none; }}
        .word-display {{ font-size: 2.2rem; color: #e17055; font-weight: bold; margin: 25px 0; padding: 20px; background: #fff5f5; border-radius: 15px; display: none; }}
        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <div class="container" id="app">
        <div class="card">
            <h1>🕵️ برا السالفة</h1>
            <p>خلك ذيب ولا تصير برا السالفة!</p>
            <div id="user-profile" class="hidden">
                <div class="avatar-box"><img id="my-avatar" class="avatar-img" src=""></div>
                <p id="welcome-msg"></p>
            </div>
            <button onclick="viewProfile()">الملف الشخصي</button>
            <button class="btn-outline" onclick="startSetup()">لعب أوفلاين</button>
        </div>
    </div>

    <script>
        const cats = {cat_json};
        let game = null;
        let currentUser = JSON.parse(localStorage.getItem('user') || 'null');

        if(currentUser) {{
            document.getElementById('user-profile').classList.remove('hidden');
            document.getElementById('welcome-msg').innerText = 'أهلاً ' + currentUser.name;
            if(currentUser.avatar) document.getElementById('my-avatar').src = currentUser.avatar;
        }}

        function startSetup() {{
            document.getElementById('app').innerHTML = `
                <div class="card">
                    <h2>إعداد اللاعبين</h2>
                    <input class="p-in" value="لاعب 1">
                    <input class="p-in" value="لاعب 2">
                    <input class="p-in" value="لاعب 3">
                    <button onclick="startGame()">ابدأ الجولة</button>
                    <button class="btn-outline" onclick="location.reload()">رجوع</button>
                </div>`;
        }

        async function viewProfile() {{
            if(!currentUser) {{
                document.getElementById('app').innerHTML = `
                    <div class="card">
                        <h2>تسجيل الدخول</h2>
                        <input id="reg-name" placeholder="اسمك">
                        <input type="file" id="reg-avatar" accept="image/*" style="display:none">
                        <button class="btn-outline" onclick="document.getElementById('reg-avatar').click()">اختر صورة</button>
                        <button onclick="register()">حفظ</button>
                    </div>`;
            } else {{
                 document.getElementById('app').innerHTML = `
                    <div class="card">
                        <div class="avatar-box"><img class="avatar-img" src="${{currentUser.avatar || ''}}"></div>
                        <h2>${{currentUser.name}}</h2>
                        <p>النقاط: 0</p>
                        <button class="btn-outline" onclick="location.reload()">رجوع</button>
                    </div>`;
            }
        }}

        async function register() {{
            const name = document.getElementById('reg-name').value;
            const file = document.getElementById('reg-avatar').files[0];
            let avatarBase64 = '';

            if(file) {{
                avatarBase64 = await new Promise(r => {{
                    const reader = new FileReader();
                    reader.onload = () => r(reader.result);
                    reader.readAsDataURL(file);
                }});
            }}

            const res = await fetch('/api/user/register', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{name, avatar: avatarBase64}})
            }});
            const data = await res.json();
            if(data.success) {{
                localStorage.setItem('user', JSON.stringify({{name, avatar: avatarBase64}}));
                location.reload();
            }}
        }}

        async function startGame() {{
            const players = Array.from(document.querySelectorAll('.p-in')).map(i => i.value);
            const res = await fetch('/api/start', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{players, category: cats[0]}})
            }});
            game = await res.json();
            game.idx = 0;
            showTurn();
        }}

        function showTurn() {{
            if (game.idx >= game.players.length) {{
                document.getElementById('app').innerHTML = `
                    <div class="card">
                        <h2>بدأ اللعب!</h2>
                        <p>كل واحد يسأل الثاني سؤال عشان تعرفون مين اللي برا السالفة.</p>
                        <button onclick="location.reload()">جولة جديدة</button>
                    </div>`;
                return;
            }
            document.getElementById('app').innerHTML = `
                <div class="card">
                    <p>مرر الجهاز لـ</p>
                    <h3>${{game.players[game.idx]}}</h3>
                    <div id="word-box" class="word-display"></div>
                    <button id="btn-reveal" onclick="reveal()">اكشف السالفة</button>
                    <button id="btn-next" class="hidden" onclick="nextP()">التالي</button>
                </div>`;
        }

        function reveal() {{
            const box = document.getElementById('word-box');
            box.innerText = game.roles[game.idx] === 'spy' ? '🕵️ أنت برا السالفة!' : '🤫 السالفة: ' + game.word;
            box.style.display = 'block';
            document.getElementById('btn-reveal').classList.add('hidden');
            document.getElementById('btn-next').classList.remove('hidden');
        }}

        function nextP() {{ game.idx++; showTurn(); }}
    </script>
</body>
</html>
    """

@app.post("/api/user/register")
async def register_user(data: dict):
    name = data.get("name")
    avatar = data.get("avatar") # Base64
    # Optional: Save to DB if connection exists
    db_query("INSERT INTO users (player_name, avatar_url, is_registered) VALUES (%s, %s, %s)",
             (name, avatar, True), commit=True)
    return {"success": True}

@app.post("/api/start")
async def start_api(data: dict):
    players = data.get('players', [])
    category = data.get('category', 'أكلات')
    words = CATEGORIES.get(category, ["بيتزا"])
    word = random.choice(words)
    roles = ["in"] * len(players)
    roles[random.randint(0, len(players)-1)] = "spy"
    return {"players": players, "word": word, "roles": roles}
