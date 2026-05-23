import os
import logging
import random
import json
import base64
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from database import init_db, db_query

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# تهيئة قاعدة البيانات عند التشغيل
@app.on_event("startup")
async def startup():
    try:
        init_db()
    except Exception as e:
        logging.error(f"Database init failed: {e}")

# بيانات الأقسام
CATEGORIES = {
    "ألعاب": ["ببجي", "فيفا", "ماينكرافت", "قراند", "فورتنايت", "كول اوف ديوتي", "روبلوكس", "فري فاير", "امونج اس", "كلاش رويال"],
    "حيوانات": ["أسد", "فيل", "زرافة", "نمر", "دب", "ثعلب", "حمار وحشي", "قطة", "كلب", "حصان"],
    "ملابس": ["قميص", "بنطلون", "فستان", "جاكيت", "تنورة", "قبعة", "حذاء", "جورب", "وشاح", "قفازات"],
    "أكلات": ["بيتزا", "برجر", "شاورما", "منسف", "كبسة", "معكرونة", "كباب", "فلافل", "سوشي", "تاكو"],
    "كرة قدم": ["ميسي", "رونالدو", "صلاح", "نيمار", "مبابي", "هالاند", "بنزيمة", "مودريتش", "ريال مدريد", "برشلونة"],
    "سيارات": ["تويوتا", "مرسيدس", "بي ام دبليو", "تسلا", "فورد", "هوندا", "نيسان", "أودي", "فيراري", "لامبورجيني"],
    "فواكه": ["تفاح", "موز", "برتقال", "فراولة", "عنب", "بطيخ", "مانجو", "أناناس", "كيوي", "خوخ"],
    "شخصيات": ["سبيستون", "سوبرمان", "باتمان", "سبايدرمان", "ميكي ماوس", "توم وجيري", "هاري بوتر", "جوكر", "ناروتو", "لوفي"],
    "كرتون": ["عدنان ولينا", "ماجد", "توم وجيري", "سلاحف النينجا", "بوكيمون", "دراغون بول", "ون بيس", "المحقق كونان", "كابتن ماجد"],
    "مشروبات": ["قهوة", "شاي", "عصير برتقال", "بيبسي", "كوكاكولا", "ماء", "حليب", "لبن", "موكا", "كابتشينو"],
    "حلويات": ["كنافة", "بقلاوة", "كيك", "دونات", "آيس كريم", "شوكولاتة", "بسبوسة", "قطايف", "بلح الشام", "سينابون"],
    "مسلسلات": ["لا كاسا دي بابيل", "بريكينج باد", "قيم اوف ثرونز", "لعبة الحبار", "دارك", "سترينجر ثينجز"],
    "انمي": ["ون بيس", "ناروتو", "هجوم العمالقة", "ديث نوت", "دراغون بول", "هنتر x هنتر"],
    "كيبوب": ["بي تي اس", "بلاكبينك", "اكسو", "توايس", "ستراي كيدز"],
    "تقنية": ["كمبيوتر", "بلايستيشن", "اكس بوكس", "ايفون", "سامسونج", "اندرويد"],
    "شركات": ["ابل", "قوقل", "مايكروسوفت", "امازون", "تسلا", "ميتا", "سوني"],
    "مدن": ["الرياض", "دبي", "القاهرة", "عمان", "الكويت", "الدوحة", "بغداد", "المنامة", "مسقط", "القدس"],
    "بلدان": ["السعودية", "مصر", "الأردن", "الإمارات", "الكويت", "قطر", "العراق", "البحرين", "عمان", "فلسطين"],
    "أجهزة": ["تلفزيون", "ثلاجة", "غسالة", "مكيف", "ميكروويف", "خلاط", "مكنسة"],
    "فضاء": ["الأرض", "المريخ", "المشتري", "زحل", "عطارد", "الزهرة", "نبتون", "الشمس", "القمر"]
}

@app.get("/", response_class=HTMLResponse)
async def get_index():
    cat_list = json.dumps(list(CATEGORIES.keys()), ensure_ascii=False)
    html_content = f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>برا السالفة</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 10px; text-align: center; color: #333; }}
        .card {{ background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 500px; margin: 15px auto; }}
        .avatar-small {{ width: 40px; height: 40px; border-radius: 50%; vertical-align: middle; margin-left: 8px; object-fit: cover; border: 1px solid #1a73e8; }}
        .avatar {{ width: 80px; height: 80px; border-radius: 50%; object-fit: cover; margin: 10px auto; border: 3px solid #1a73e8; display: block; }}
        h1 {{ color: #1a73e8; margin-bottom: 20px; font-size: 24px; }}
        input, select, button {{ width: 100%; padding: 14px; margin: 8px 0; border: 1px solid #ddd; border-radius: 10px; box-sizing: border-box; font-size: 16px; outline: none; }}
        button {{ background-color: #1a73e8; color: white; border: none; cursor: pointer; font-weight: bold; transition: 0.2s; }}
        button:active {{ transform: scale(0.98); opacity: 0.9; }}
        .secondary {{ background-color: #34a853; }}
        .warning {{ background-color: #fbbc05; color: black; }}
        .danger {{ background-color: #ea4335; }}
        .word-box {{ font-size: 30px; font-weight: bold; color: #d93025; background: #fce8e6; padding: 20px; border-radius: 10px; margin: 20px 0; display: none; cursor: pointer; }}
        .p-name {{ margin-bottom: 5px; }}
        .upload-area {{ border: 2px dashed #ccc; padding: 20px; border-radius: 10px; cursor: pointer; margin: 10px 0; }}
    </style>
</head>
<body>
    <div id="app">
        <div class="card">
            <h1>جاري التحميل...</h1>
        </div>
    </div>

    <script>
        const CATEGORIES_LIST = {cat_list};
        const state = {{
            user: JSON.parse(localStorage.getItem('user') || 'null'),
            view: 'auth',
            gameState: null
        }};

        async function apiPost(url, data) {{
            try {{
                const res = await fetch('/api' + url, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(data)
                }});
                return await res.json();
            }} catch (e) {{
                return {{ ok: false, error: "فشل الاتصال بالسيرفر" }};
            }}
        }}

        function render() {{
            const root = document.getElementById('app');
            if (!state.user) return renderAuth(root);

            switch(state.view) {{
                case 'profile': return renderProfile(root);
                case 'main': return renderMain(root);
                case 'offline_setup': return renderOfflineSetup(root);
                case 'in_game': return renderInGame(root);
                case 'online_setup': return renderOnlineSetup(root);
                default: return renderMain(root);
            }}
        }

        function renderAuth(root) {{
            root.innerHTML = `
                <div class="card">
                    <h1>برا السالفة - دخول</h1>
                    <div id="login-form">
                        <input type="text" id="username" placeholder="اليوزر">
                        <input type="password" id="password" placeholder="كلمة المرور">
                        <button onclick="login()">دخول</button>
                        <p onclick="toggleAuth(true)" style="cursor:pointer; color:#1a73e8">ليس لديك حساب؟ سجل الآن</p>
                    </div>
                    <div id="reg-form" style="display:none">
                        <input type="text" id="reg-name" placeholder="اسمك بالعربي">
                        <input type="text" id="reg-user" placeholder="يوزر من 4 خانات">
                        <input type="password" id="reg-pass" placeholder="كلمة المرور">
                        <button class="secondary" onclick="register()">إنشاء حساب</button>
                        <p onclick="toggleAuth(false)" style="cursor:pointer; color:#1a73e8">لديك حساب؟ سجل دخول</p>
                    </div>
                </div>
            `;
        }

        function toggleAuth(isReg) {{
            document.getElementById('login-form').style.display = isReg ? 'none' : 'block';
            document.getElementById('reg-form').style.display = isReg ? 'block' : 'none';
        }

        async function login() {{
            const res = await apiPost('/login', {{
                username: document.getElementById('username').value,
                password: document.getElementById('password').value
            }});
            if (res.ok) {{
                state.user = res.user;
                localStorage.setItem('user', JSON.stringify(res.user));
                state.view = 'main';
                render();
            }} else alert(res.error);
        }

        async function register() {{
            const res = await apiPost('/register', {{
                name: document.getElementById('reg-name').value,
                username: document.getElementById('reg-user').value,
                password: document.getElementById('reg-pass').value
            }});
            if (res.ok) {{
                alert('تم التسجيل بنجاح! سجل دخولك الآن');
                toggleAuth(false);
            }} else alert(res.error);
        }

        function renderMain(root) {{
            const avatar = state.user.avatar || 'https://cdn-icons-png.flaticon.com/512/149/149071.png';
            root.innerHTML = `
                <div class="card">
                    <div style="display:flex; align-items:center; cursor:pointer; margin-bottom:20px" onclick="state.view='profile'; render()">
                        <img src="${{avatar}}" class="avatar-small">
                        <b>${{state.user.name}}</b>
                    </div>
                    <h1>برا السالفة</h1>
                    <button class="secondary" style="padding:30px" onclick="state.view='offline_setup'; render()">لعب أوفلاين (جهاز واحد)</button>
                    <button style="padding:30px" onclick="state.view='online_setup'; render()">لعب أونلاين (كل واحد بجهازه)</button>
                </div>
            `;
        }

        function renderProfile(root) {{
            const avatar = state.user.avatar || 'https://cdn-icons-png.flaticon.com/512/149/149071.png';
            root.innerHTML = `
                <div class="card">
                    <h1>الملف الشخصي</h1>
                    <img src="${{avatar}}" class="avatar" id="profile-img">
                    <div class="upload-area" onclick="document.getElementById('file-input').click()">
                        اضغط لتغيير صورتك 📸
                        <input type="file" id="file-input" style="display:none" onchange="uploadAvatar(this)" accept="image/*">
                    </div>
                    <p>الاسم: <b>${{state.user.name}}</b></p>
                    <button class="danger" onclick="state.view='main'; render()">رجوع</button>
                    <button class="warning" style="margin-top:20px" onclick="logout()">تسجيل خروج</button>
                </div>
            `;
        }

        function logout() {{
            localStorage.clear();
            state.user = null;
            state.view = 'auth';
            render();
        }

        async function uploadAvatar(input) {{
            if (!input.files[0]) return;
            const file = input.files[0];
            if (file.size > 500000) return alert('الصورة كبيرة جداً! اختر صورة أقل من 500 كيلوبايت');

            const reader = new FileReader();
            reader.onload = async (e) => {{
                const base64Data = e.target.result;
                const res = await apiPost('/update-avatar', {{ user_id: state.user.id, image: base64Data }});
                if (res.ok) {{
                    state.user.avatar = base64Data;
                    localStorage.setItem('user', JSON.stringify(state.user));
                    render();
                }}
            }};
            reader.readAsDataURL(file);
        }

        function renderOfflineSetup(root) {{
            let cats = CATEGORIES_LIST.map(c => `<option>${{c}}</option>`).join('');
            root.innerHTML = `
                <div class="card">
                    <h1>إعداد اللعبة</h1>
                    <div id="players">
                        <input class="p-input" placeholder="لاعب 1">
                        <input class="p-input" placeholder="لاعب 2">
                        <input class="p-input" placeholder="لاعب 3">
                    </div>
                    <button class="warning" onclick="addPlayerField()">+ إضافة لاعب</button>
                    <label>القسم:</label>
                    <select id="selected-cat">${{cats}}</select>
                    <button class="secondary" onclick="startOffline()">ابدأ اللعب</button>
                    <button class="danger" onclick="state.view='main'; render()">رجوع</button>
                </div>
            `;
        }

        function addPlayerField() {{
            const input = document.createElement('input');
            input.className = 'p-input';
            input.placeholder = 'لاعب جديد';
            document.getElementById('players').appendChild(input);
        }

        async function startOffline() {{
            const players = Array.from(document.querySelectorAll('.p-input')).map(i => i.value).filter(v => v);
            if (players.length < 3) return alert('يجب إضافة 3 لاعبين على الأقل');

            const res = await apiPost('/start-offline', {{
                players: players,
                category: document.getElementById('selected-cat').value
            }});
            state.gameState = res;
            state.view = 'in_game';
            render();
        }

        function renderInGame(root) {{
            const gs = state.gameState;
            const name = gs.players[gs.current_idx];
            root.innerHTML = `
                <div class="card">
                    <h2>دور: <span style="color:#1a73e8">${{name}}</span></h2>
                    <p>مرر الجهاز لـ ${{name}} واضغط لرؤية السالفة</p>
                    <div id="word-box" class="word-box" onclick="this.style.display='none'"></div>
                    <button class="warning" id="show-btn" onclick="showWord()">اكشف السالفة</button>
                    <button id="next-btn" style="display:none" onclick="nextPlayer()">اللاعب التالي</button>
                </div>
            `;
        }

        function showWord() {{
            const gs = state.gameState;
            const box = document.getElementById('word-box');
            box.innerText = gs.roles[gs.current_idx] === 'spy' ? 'أنت برا السالفة!' : gs.word;
            box.style.display = 'block';
            document.getElementById('show-btn').style.display = 'none';
            document.getElementById('next-btn').style.display = 'block';
        }

        function nextPlayer() {{
            state.gameState.current_idx++;
            if (state.gameState.current_idx >= state.gameState.players.length) {{
                alert('انتهى توزيع السالفة! ابدأوا النقاش');
                state.view = 'main';
            }}
            render();
        }

        function renderOnlineSetup(root) {{
            root.innerHTML = `
                <div class="card">
                    <h1>لعب أونلاين</h1>
                    <p>هذه الميزة قيد التطوير حالياً...</p>
                    <button class="danger" onclick="state.view='main'; render()">رجوع</button>
                </div>
            `;
        }

        window.onload = render;
    </script>
</body>
</html>
    """
    return html_content

# --- API Endpoints ---

class AuthData(BaseModel):
    name: str = ""
    username: str
    password: str

@app.post("/api/register")
async def api_register(data: AuthData):
    if len(data.username) < 4:
        return {"ok": False, "error": "اليوزر يجب أن يكون 4 خانات على الأقل"}

    try:
        existing = db_query("SELECT 1 FROM users WHERE username_key = %s", (data.username,))
        if existing:
            return {"ok": False, "error": "هذا اليوزر مستخدم من قبل"}

        uid = random.randint(100000, 999999)
        db_query("INSERT INTO users (user_id, player_name, username_key, password_key, is_registered) VALUES (%s, %s, %s, %s, TRUE)",
                 (uid, data.name, data.username, data.password), commit=True)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": f"خطأ في التسجيل: {str(e)}"}

@app.post("/api/login")
async def api_login(data: AuthData):
    try:
        user = db_query("SELECT user_id, player_name, avatar_url FROM users WHERE username_key = %s AND password_key = %s",
                        (data.username, data.password))
        if user:
            return {
                "ok": True,
                "user": {
                    "id": user[0]['user_id'],
                    "name": user[0]['player_name'],
                    "avatar": user[0]['avatar_url']
                }
            }
        return {"ok": False, "error": "اليوزر أو كلمة المرور خاطئة"}
    except Exception as e:
        return {"ok": False, "error": f"خطأ في الدخول: {str(e)}"}

class AvatarUpdate(BaseModel):
    user_id: int
    image: str

@app.post("/api/update-avatar")
async def api_update_avatar(data: AvatarUpdate):
    try:
        db_query("UPDATE users SET avatar_url = %s WHERE user_id = %s", (data.image, data.user_id), commit=True)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

class OfflineStart(BaseModel):
    players: list
    category: str

@app.post("/api/start-offline")
async def api_start_offline(data: OfflineStart):
    word = random.choice(CATEGORIES.get(data.category, ["خطأ"]))
    roles = ["in"] * len(data.players)
    spy_idx = random.randint(0, len(data.players) - 1)
    roles[spy_idx] = "spy"
    return {"players": data.players, "word": word, "roles": roles, "current_idx": 0}
