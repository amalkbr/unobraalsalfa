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
    init_db()

# بيانات الأقسام
CATEGORIES = {
    "الللعاب": ["PUBG", "FIFA", "Minecraft", "GTA V", "Fortnite", "Call of Duty", "Roblox", "Free Fire", "Among Us", "Clash Royale"],
    "حيوانات": ["أسد", "فيل", "زرافة", "نمر", "دب", "ثعلب", "حمار وحشي", "قطة", "كلب", "حصان"],
    "ملابس": ["قميص", "بنطلون", "فستان", "جاكيت", "تنورة", "قبعة", "حذاء", "جورب", "وشاح", "قفازات"],
    "اكلات": ["بيتزا", "برجر", "شاورما", "منسف", "كبسة", "معكرونة", "كباب", "فلافل", "سوشي", "تاكو"],
    "كوره": ["ميسي", "رونالدو", "صلاح", "نيمار", "مبابي", "هالاند", "بنزيمة", "مودريتش", "ريال مدريد", "برشلونة"],
    "سيارات": ["تويوتا", "مرسيدس", "بي ام دبليو", "تسلا", "فورد", "هوندا", "نيسان", "أودي", "فيراري", "لامبورجيني"],
    "فواكه": ["تفاح", "موز", "برتقال", "فراولة", "عنب", "بطيخ", "مانجو", "أناناس", "كيوي", "خوخ"],
    "شخصيات": ["سبيستون", "سوبرمان", "باتمان", "سبايدرمان", "ميكي ماوس", "توم وجيري", "هاري بوتر", "جوكر", "ناروتو", "لوفي"],
    "كرتون": ["عدنان ولينا", "ماجد", "توم وجيري", "سلاحف النينجا", "بوكيمون", "دراغون بول", "ون بيس", "المحقق كونان", "كابتن ماجد", "بوكيمون"],
    "مشروبات": ["قهوة", "شاي", "عصير برتقال", "بيبسي", "كوكاكولا", "ماء", "حليب", "لبن", "موكا", "كابتشينو"],
    "حلويات": ["كنافة", "بقلاوة", "كيك", "دونات", "آيس كريم", "شوكولاتة", "بسبوسة", "قطايف", "بلح الشام", "سينابون"],
    "مسلسلات": ["La Casa de Papel", "Breaking Bad", "Game of Thrones", "Squid Game", "Dark", "Stranger Things", "The Witcher", "Friends", "The Office", "Peaky Blinders"],
    "انمي": ["One Piece", "Naruto", "Attack on Titan", "Death Note", "Dragon Ball", "Hunter x Hunter", "Jujutsu Kaisen", "Demon Slayer", "Tokyo Ghoul", "Bleach"],
    "كيبوب": ["BTS", "Blackpink", "EXO", "Twice", "Stray Kids", "Red Velvet", "NCT", "Tomorrow X Together", "Enhypen", "Seventeen"],
    "كيمز": ["PC", "PlayStation", "Xbox", "Nintendo Switch", "Mobile Gaming", "VR", "Streamer", "Discord", "Steam", "Epic Games"],
    "شركات": ["Apple", "Google", "Samsung", "Microsoft", "Amazon", "Tesla", "Meta", "Sony", "Huawei", "Nike"],
    "مدن": ["الرياض", "دبي", "القاهرة", "عمان", "الكويت", "الدوحة", "بغداد", "المنامة", "مسقط", "القدس"],
    "بلدان": ["السعودية", "مصر", "الأردن", "الإمارات", "الكويت", "قطر", "العراق", "البحرين", "عمان", "فلسطين"],
    "اجهزة كهربائية": ["تلفزيون", "ثلاجة", "غسالة", "مكيف", "ميكروويف", "خلاط", "مكنسة", "كواية", "فرن", "سخان"],
    "كواكب": ["الأرض", "المريخ", "المشتري", "زحل", "عطارد", "الزهرة", "أورانوس", "نبتون", "بلوتو", "الشمس"]
}

# --- الواجهة البرمجية (HTML & CSS) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>أونو وبرا السالفة</title>
    <link rel="manifest" href="/static/manifest.json">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 10px; text-align: center; color: #333; overflow-x: hidden; }
        .card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 500px; margin: 15px auto; transition: transform 0.3s; }
        .avatar { width: 80px; height: 80px; border-radius: 50%; object-fit: cover; margin: 10px auto; border: 3px solid #1a73e8; display: block; }
        .avatar-small { width: 40px; height: 40px; border-radius: 50%; vertical-align: middle; margin-left: 8px; object-fit: cover; border: 1px solid #1a73e8; }
        .upload-area { border: 2px dashed #ccc; padding: 20px; border-radius: 10px; cursor: pointer; margin: 10px 0; }
        h1 { color: #1a73e8; margin-bottom: 20px; font-size: 24px; }
        input, select, button { width: 100%; padding: 14px; margin: 8px 0; border: 1px solid #ddd; border-radius: 10px; box-sizing: border-box; font-size: 16px; outline: none; }
        button { background-color: #1a73e8; color: white; border: none; cursor: pointer; font-weight: bold; transition: 0.2s; -webkit-tap-highlight-color: transparent; }
        button:active { transform: scale(0.98); opacity: 0.9; }
        .secondary { background-color: #34a853; }
        .warning { background-color: #fbbc05; color: black; }
        .danger { background-color: #ea4335; }
        .link-text { color: #1a73e8; cursor: pointer; text-decoration: underline; font-weight: bold; }
        .share-box { background: #e8f0fe; padding: 15px; border-radius: 10px; margin-top: 15px; word-break: break-all; border: 1px dashed #1a73e8; }
        .word-box { font-size: 30px; font-weight: bold; color: #d93025; background: #fce8e6; padding: 20px; border-radius: 10px; margin: 20px 0; display: none; }
    </style>
</head>
<body>
    <div id="app"></div>

    <script>
        const API = {
            async post(url, data) {
                const res = await fetch('/api' + url, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
                return await res.json();
            }
        };

        const state = {
            user: JSON.parse(localStorage.getItem('user') || 'null'),
            view: 'auth',
            pendingRoom: localStorage.getItem('pending_room'),
            gameState: null
        };

        function render() {
            const root = document.getElementById('app');
            if (!state.user) return renderAuth(root);

            switch(state.view) {
                case 'profile': return renderProfile(root);
                case 'select': return renderSelect(root);
                case 'bara_main': return renderBaraMain(root);
                case 'bara_offline': return renderBaraOffline(root);
                case 'bara_online': return renderBaraOnline(root);
                case 'in_game': return renderInGame(root);
                default: renderSelect(root);
            }
        }

        function renderAuth(root) {
            root.innerHTML = `
                <div class="card">
                    <h1>أهلاً بك في "السالفة"</h1>
                    <div id="login-form">
                        <input type="text" id="l-user" placeholder="اليوزر">
                        <input type="password" id="l-pass" placeholder="كلمة المرور">
                        <button onclick="login()">دخول</button>
                        <p>ليس لديك حساب؟ <span class="link-text" onclick="toggleAuth(true)">سجل الآن</span></p>
                    </div>
                    <div id="reg-form" style="display:none">
                        <input type="text" id="r-name" placeholder="اسمك بالعربي">
                        <input type="text" id="r-user" placeholder="يوزر من 4 خانات">
                        <input type="password" id="r-pass" placeholder="كلمة المرور">
                        <button class="secondary" onclick="register()">إنشاء حساب</button>
                        <p>لديك حساب؟ <span class="link-text" onclick="toggleAuth(false)">دخول</span></p>
                    </div>
                </div>
            `;
        }

        async function login() {
            const res = await API.post('/login', {username: id('l-user').value, password: id('l-pass').value});
            if(res.ok) { saveUser(res.user); } else alert(res.error);
        }

        async function register() {
            const res = await API.post('/register', {name: id('r-name').value, username: id('r-user').value, password: id('r-pass').value});
            if(res.ok) { alert('تم بنجاح! سجل دخول الآن'); toggleAuth(false); } else alert(res.error);
        }

        function saveUser(user) {
            localStorage.setItem('user', JSON.stringify(user));
            state.user = user;
            state.view = state.pendingRoom ? 'vote' : 'select';
            render();
        }

        function toggleAuth(isReg) {
            id('login-form').style.display = isReg ? 'none' : 'block';
            id('reg-form').style.display = isReg ? 'block' : 'none';
        }

        function renderSelect(root) {
            const avatar = state.user.avatar || 'https://cdn-icons-png.flaticon.com/512/149/149071.png';
            root.innerHTML = `
                <div class="card">
                    <div style="text-align:right; display:flex; align-items:center; cursor:pointer" onclick="state.view='profile'; render()">
                        <img src="${avatar}" class="avatar-small">
                        <b>${state.user.name}</b>
                    </div>
                    <h1>اختر اللعبة</h1>
                    <button class="danger" style="padding:40px" onclick="alert('أونو قيد التطوير...')">أونو (UNO) 🃏</button>
                    <button class="secondary" style="padding:40px" onclick="state.view='bara_main'; render();">برا السالفة 🕵️</button>
                </div>
            `;
        }

        function renderProfile(root) {
            const avatar = state.user.avatar || 'https://cdn-icons-png.flaticon.com/512/149/149071.png';
            root.innerHTML = `
                <div class="card">
                    <h1>الملف الشخصي</h1>
                    <img src="${avatar}" class="avatar">
                    <div class="upload-area" onclick="id('file-input').click()">
                        اضغط لتغيير صورتك (مجاناً) 📸
                        <input type="file" id="file-input" style="display:none" onchange="uploadAvatar(this)" accept="image/*">
                    </div>
                    <p>الاسم: <b>${state.user.name}</b></p>
                    <button class="danger" onclick="state.view='select'; render()">رجوع</button>
                    <button class="warning" style="margin-top:20px" onclick="localStorage.clear(); location.reload()">تسجيل خروج</button>
                </div>
            `;
        }

        async function uploadAvatar(input) {
            if (!input.files[0]) return;
            const file = input.files[0];
            if (file.size > 1024 * 1024) return alert('الصورة كبيرة جداً! اختر صورة أقل من 1 ميجا');

            const reader = new FileReader();
            reader.onload = async (e) => {
                const base64Data = e.target.result;
                const res = await API.post('/update-avatar', {user_id: state.user.id, image: base64Data});
                if(res.ok) {
                    state.user.avatar = base64Data;
                    localStorage.setItem('user', JSON.stringify(state.user));
                    render();
                }
            };
            reader.readAsDataURL(file);
        }

        function renderBaraMain(root) {
            root.innerHTML = `
                <div class="card">
                    <h1>برا السالفة</h1>
                    <button class="warning" onclick="state.view='bara_offline'; render();">أوفلاين (جهاز واحد)</button>
                    <button onclick="state.view='bara_online'; render();">أونلاين (كل واحد بجهازه)</button>
                    <button class="danger" onclick="state.view='select'; render();">رجوع</button>
                </div>
            `;
        }

        function renderBaraOffline(root) {
            let cats = ${JSON.stringify(list(CATEGORIES.keys()))}.map(c => `<option>${c}</option>`).join('');
            root.innerHTML = `
                <div class="card">
                    <h2>إعداد أوفلاين</h2>
                    <div id="p-list">
                        <input class="p-name" placeholder="لاعب 1">
                        <input class="p-name" placeholder="لاعب 2">
                        <input class="p-name" placeholder="لاعب 3">
                    </div>
                    <button class="warning" onclick="addP()">+ إضافة لاعب</button>
                    <label>القسم:</label><select id="cat">${cats}</select>
                    <label>نقاط الفوز:</label>
                    <select id="pts"><option>5</option><option>10</option><option>20</option></select>
                    <button onclick="startOffline()">ابدأ اللعب</button>
                    <button class="danger" onclick="state.view='bara_main'; render();">رجوع</button>
                </div>
            `;
        }

        function addP() {
            const i = document.createElement('input'); i.className = 'p-name'; i.placeholder = 'لاعب جديد';
            id('p-list').appendChild(i);
        }

        async function startOffline() {
            const players = Array.from(document.querySelectorAll('.p-name')).map(i => i.value).filter(v => v);
            if(players.length < 3) return alert('أقل شيء 3 لاعبين');
            const res = await API.post('/start-offline', {players, category: id('cat').value, goal: id('pts').value});
            state.gameState = res;
            state.view = 'in_game';
            render();
        }

        function renderInGame(root) {
            const gs = state.gameState;
            root.innerHTML = `
                <div class="card">
                    <h2>دور: <span style="color:#1a73e8">${gs.players[gs.current_idx]}</span></h2>
                    <p>اضغط على المربع لرؤية "السالفة"</p>
                    <div id="word-box" class="word-box" onclick="this.style.display='none'"></div>
                    <button class="warning" onclick="showWord()">اكشف السالفة</button>
                    <button id="next-p-btn" style="display:none" onclick="nextPlayer()">اللاعب التالي</button>
                </div>
            `;
        }

        function showWord() {
            const gs = state.gameState;
            const box = id('word-box');
            box.innerText = gs.roles[gs.current_idx] === 'spy' ? 'أنت برا السالفة!' : gs.word;
            box.style.display = 'block';
            id('next-p-btn').style.display = 'block';
        }

        function nextPlayer() {
            state.gameState.current_idx++;
            if(state.gameState.current_idx >= state.gameState.players.length) {
                alert('انتهى التوزيع! ابدأوا النقاش الآن');
                state.view = 'select';
            }
            render();
        }

        function renderBaraOnline(root) {
            root.innerHTML = `
                <div class="card">
                    <h1>غرفة أونلاين</h1>
                    <label>الحد الأقصى:</label>
                    <select id="max-p"><option>3</option><option>5</option><option>8</option></select>
                    <button onclick="createRoom()">إنشاء الرابط</button>
                    <div id="room-link-box" class="share-box" style="display:none">
                        <p>أرسل الرابط لأصحابك:</p>
                        <b id="room-url"></b><br><br>
                        <button class="secondary" onclick="copyUrl()">نسخ الرابط ✅</button>
                    </div>
                    <button class="danger" onclick="state.view='bara_main'; render();">رجوع</button>
                </div>
            `;
        }

        async function createRoom() {
            const rid = Math.random().toString(36).substring(2, 7).toUpperCase();
            const res = await API.post('/room-create', {room_id: rid, max: id('max-p').value});
            if(res.ok) {
                const url = window.location.origin + '/join/' + rid;
                id('room-url').innerText = url;
                id('room-link-box').style.display = 'block';
            }
        }

        function copyUrl() { navigator.clipboard.writeText(id('room-url').innerText).then(() => alert('تم النسخ!')); }

        const id = (i) => document.getElementById(i);
        window.onload = render;
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTML_TEMPLATE

@app.get("/join/{room_id}", response_class=HTMLResponse)
async def join_room(room_id: str):
    return f"""<script>localStorage.setItem('pending_room', '{room_id}'); window.location.href = '/';</script>"""

# --- API ---

class RegData(BaseModel):
    name: str = ""
    username: str
    password: str

@app.post("/api/register")
async def api_register(data: RegData):
    existing = db_query("SELECT 1 FROM users WHERE username_key = %s", (data.username,))
    if existing: return {"ok": False, "error": "اليوزر مأخوذ"}
    uid = random.randint(100000, 999999)
    db_query("INSERT INTO users (user_id, player_name, username_key, password_key, is_registered) VALUES (%s, %s, %s, %s, TRUE)",
             (uid, data.name, data.username, data.password), commit=True)
    return {"ok": True}

@app.post("/api/login")
async def api_login(data: RegData):
    user = db_query("SELECT user_id, player_name, avatar_url FROM users WHERE username_key = %s AND password_key = %s", (data.username, data.password))
    if user: return {"ok": True, "user": {"id": user[0]['user_id'], "name": user[0]['player_name'], "avatar": user[0]['avatar_url']}}
    return {"ok": False, "error": "اليوزر أو الباسوورد خطأ"}

class AvatarUpdate(BaseModel):
    user_id: int
    image: str # Base64 string

@app.post("/api/update-avatar")
async def api_update_avatar(data: AvatarUpdate):
    db_query("UPDATE users SET avatar_url = %s WHERE user_id = %s", (data.image, data.user_id), commit=True)
    return {"ok": True}

class OfflineStart(BaseModel):
    players: list
    category: str
    goal: int

@app.post("/api/start-offline")
async def api_start_offline(data: OfflineStart):
    word = random.choice(CATEGORIES.get(data.category, ["خطأ"]))
    roles = ["in"] * len(data.players)
    spy_idx = random.randint(0, len(data.players) - 1)
    roles[spy_idx] = "spy"
    return {"players": data.players, "word": word, "roles": roles, "current_idx": 0}

class RoomCreate(BaseModel):
    room_id: str
    max: int

@app.post("/api/room-create")
async def api_room_create(data: RoomCreate):
    db_query("INSERT INTO rooms (room_id, max_players, status) VALUES (%s, %s, 'waiting')", (data.room_id, data.max), commit=True)
    return {"ok": True}
