from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import json
import random
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

# --- Database Connection ---
def get_db_conn():
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        try: return psycopg2.connect(db_url, sslmode='require')
        except: return None
    return None

# --- Game Data ---
CATEGORIES = {
    "سيارات": ["تويوتا", "مرسيدس", "فورد", "تسلا", "نيسان", "هوندا", "بي ام دبليو", "لكزس", "مازدا", "كيا", "باجيرو", "لاند كروزر", "شفروليه", "كامري"],
    "انمي": ["ون بيس", "ناروتو", "هجوم العمالقة", "دراجون بول", "هنتر", "بليتش", "كونان", "ديمون سلاير", "جوجوتسو", "ديث نوت", "بلاك كلوفر"],
    "أكلات": ["بيتزا", "برجر", "شاورما", "منسف", "كبسة", "فلافل", "مندي", "باستا", "دولمة", "برياني", "مسحب", "كبة", "بخاري", "مقلوبة"],
    "فواكه": ["تفاح", "موز", "مانجو", "فراولة", "بطيخ", "عنب", "برتقال", "أناناس", "كيوي", "توت", "كرز", "رمان", "افوكادو"],
    "أجهزة": ["آيفون", "بليستيشن", "لابتوب", "تلفزيون", "ساعة ذكية", "كاميرا", "ايباد", "اكس بوكس", "بي سي", "سماعات", "غسالة", "مكيف"]
}

@app.get("/", response_class=HTMLResponse)
async def home(): return HTML_TEMPLATE

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
        return {"success": True}
    except: return {"success": False, "msg": "اليوزر نيم مستخدم مسبقاً"}
    finally: conn.close()

@app.post("/api/auth/login")
async def login(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "قاعدة البيانات غير متصلة"}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT username_key, player_name, password_key FROM users WHERE username_key = %s AND password_key = %s",
                        (data['username'], data['password']))
            user = cur.fetchone()
            return {"success": True, "user": user} if user else {"success": False, "msg": "بيانات الدخول خاطئة"}
    finally: conn.close()

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
    words = CATEGORIES.get(category, CATEGORIES["أكلات"])
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

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>برا السالفة | المجلس</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #6c5ce7; --bg: #0f0c29; --card: #1b1464; --accent: #f9ca24; --error: #eb4d4b; }
        body { font-family: 'Cairo', sans-serif; background: var(--bg); color: white; margin: 0; min-height: 100vh; }
        .flex-center { display: flex; justify-content: center; align-items: center; min-height: 100vh; flex-direction: column; }
        .container { width: 95%; max-width: 500px; text-align: center; padding: 20px; box-sizing: border-box; }
        .card { background: var(--card); padding: 30px; border-radius: 30px; box-shadow: 0 15px 35px rgba(0,0,0,0.6); border: 2px solid #3c339e; animation: fadeIn 0.3s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        h1 { font-weight: 900; color: #a29bfe; margin-bottom: 25px; font-size: 32px; }
        input, select { width: 100%; padding: 15px; margin: 10px 0; border-radius: 15px; border: 2px solid #2f278c; background: #0f0c29; color: white; font-size: 16px; box-sizing: border-box; outline: none; }
        button { width: 100%; padding: 16px; margin: 12px 0; border-radius: 18px; border: none; background: linear-gradient(45deg, #6c5ce7, #a29bfe); color: white; font-weight: bold; cursor: pointer; font-size: 18px; transition: 0.3s; }
        button:hover { transform: translateY(-3px); }
        .sidebar { position: fixed; right: -280px; top: 0; width: 280px; height: 100%; background: #130f40; transition: 0.4s; z-index: 1000; padding: 30px 20px; box-sizing: border-box; border-left: 2px solid var(--primary); }
        .sidebar.open { right: 0; }
        .menu-btn { position: fixed; right: 20px; top: 20px; font-size: 28px; cursor: pointer; z-index: 1001; background: var(--card); width: 50px; height: 50px; border-radius: 15px; text-align: center; line-height: 50px; }
        .vote-item { background: #2f278c; padding: 18px; margin: 10px 0; border-radius: 20px; cursor: pointer; transition: 0.2s; font-weight: bold; }
        .vote-item:hover { background: var(--primary); transform: scale(1.02); }
        .hidden { display: none !important; }
        .q-badge { background: var(--error); padding: 4px 12px; border-radius: 8px; font-size: 13px; margin-bottom: 15px; display: inline-block; }
        .shuffling { animation: rotate 1s infinite linear; font-size: 50px; margin: 20px; display:inline-block; }
        @keyframes rotate { from { transform: rotate(0); } to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="menu-btn" onclick="toggleSidebar()">☰</div>
    <div id="sidebar" class="sidebar">
        <h2 style="color:var(--accent)">القائمة</h2>
        <div style="background:#1b1464; padding:15px; border-radius:15px; margin:20px 0;">
            <p id="user-display" style="margin:0; font-weight:bold;">زائر</p>
        </div>
        <button style="background:var(--primary); font-size:14px;" onclick="showEditProfile()">تعديل بيانات الحساب</button>
        <button style="background:var(--error); font-size:14px;" onclick="logout()">تسجيل الخروج</button>
        <button style="background:#636e72; font-size:14px;" onclick="toggleSidebar()">إغلاق</button>
    </div>
    <div class="flex-center"><div class="container" id="main-ui"></div></div>
    <script>
        let currentUser = JSON.parse(localStorage.getItem('user')) || null;
        let game = null;
        let p_votes = {};

        function init() { currentUser ? showMenu() : showAuth(); updateSidebar(); }

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
            const res = await fetch('/api/auth/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: u_name.value, password: u_pass.value})});
            const d = await res.json();
            if(d.success) { localStorage.setItem('user', JSON.stringify(d.user)); currentUser = d.user; init(); } else alert(d.msg);
        }

        async function register() {
            if(!u_name.value || !u_pass.value || !r_nick.value) return alert("املأ كل الحقول!");
            const res = await fetch('/api/auth/register', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: u_name.value, password: u_pass.value, name: r_nick.value})});
            const d = await res.json();
            d.success ? alert("تم التسجيل! ادخل الآن") : alert(d.msg);
        }

        function showMenu() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h1>ابدأ اللعب</h1>
                    <button onclick="alert('الأونلاين قريباً!')">🌐 أونلاين</button>
                    <button style="background:#e056fd" onclick="showSetup(1)">🏠 أوفلاين (مجلس)</button>
                </div>`;
        }

        function showEditProfile() {
            toggleSidebar();
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>تعديل بياناتي</h2>
                    <p style="margin-bottom:0">اليوزر نيم:</p>
                    <input id="edit_u" value="${currentUser.username_key}">
                    <p style="margin-bottom:0">الاسم المستعار:</p>
                    <input id="edit_n" value="${currentUser.player_name}">
                    <p style="margin-bottom:0">الباسوورد الجديد:</p>
                    <input id="edit_p" type="password" value="${currentUser.password_key}">
                    <button onclick="updateProfile()">حفظ التعديلات</button>
                    <button style="background:#636e72" onclick="showMenu()">إلغاء</button>
                </div>`;
        }

        async function updateProfile() {
            const res = await fetch('/api/auth/update', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    old_username: currentUser.username_key,
                    username: edit_u.value,
                    password: edit_p.value,
                    name: edit_n.value
                })
            });
            const d = await res.json();
            if(d.success) { alert("تم التحديث! سجل دخولك مجدداً"); logout(); } else alert(d.msg);
        }

        function showSetup(step) {
            if(step === 1) {
                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2>عدد اللاعبين</h2>
                        <input type="number" id="p_count" value="3" min="3">
                        <button onclick="showSetup(2)">التالي</button>
                        <button style="background:#636e72" onclick="showMenu()">رجوع</button>
                    </div>`;
            } else if(step === 2) {
                const n = Math.max(3, parseInt(document.getElementById('p_count').value));
                window.pCountSave = n;
                let h = '';
                for(let i=1; i<=n; i++) h += `<input class="pn" placeholder="اللاعب ${i}" value="لاعب ${i}">`;
                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2>أسماء اللاعبين</h2>
                        <div id="p_inputs">${h}</div>
                        <button onclick="showSetup(3)">التالي</button>
                        <button style="background:#636e72" onclick="showSetup(1)">رجوع</button>
                    </div>`;
            } else if(step === 3) {
                window.pNamesSave = Array.from(document.querySelectorAll('.pn')).map(i => i.value);
                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2>إعدادات الجولة</h2>
                        <select id="g_cat"><option value="أكلات">فئة الأكلات</option><option value="سيارات">فئة السيارات</option><option value="انمي">فئة الانمي</option><option value="فواكه">فئة الفواكه</option><option value="أجهزة">فئة الأجهزة</option></select>
                        <p>حد الفوز:</p>
                        <select id="win_limit"><option>5</option><option selected>10</option><option>20</option></select>
                        <button onclick="start()">ابدأ اللعب الآن</button>
                        <button style="background:#636e72" onclick="showSetup(2)">رجوع</button>
                    </div>`;
            }
        }

        async function start() {
            const players = window.pNamesSave;
            const res = await fetch('/api/game/start', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({players, category: g_cat.value})});
            game = await res.json();
            game.players = players;
            game.curr = 0;
            game.qIdx = 0; // عداد الأسئلة
            showRole();
        }

        function showRole() {
            if(game.curr >= game.players.length) { showPhase1(); return; }
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <p>مرر الجهاز لـ</p><h2 style="color:var(--accent)">${game.players[game.curr]}</h2>
                    <div id="box" class="hidden" style="background:#0f0c29; padding:20px; border-radius:20px; margin:20px 0;">
                        <h3>${game.roles[game.curr] === 'spy' ? '🕵️ أنت برة السالفة!' : '🤫 السالفة هي: ' + game.word}</h3>
                    </div>
                    <button onclick="document.getElementById('box').classList.remove('hidden'); this.style.display='none'; document.getElementById('bnxt').style.display='block'">اكشف الدور</button>
                    <button id="bnxt" style="display:none" onclick="game.curr++; showRole()">فهمت، التالي</button>
                </div>`;
        }

        function showPhase1() {
            if(game.qIdx >= game.q_seq.length) { showPhase2(game.players[0]); return; }
            const q = game.q_seq[game.qIdx];
            document.getElementById('main-ui').innerHTML = `
                <div class="card"><span class="q-badge">مرحلة إجبارية</span>
                    <div style="font-size:24px; margin:30px 0;">
                        <b style="color:#a29bfe">${q.f}</b> يسأل <b style="color:#ff7675">${q.t}</b>
                    </div>
                    <button onclick="game.qIdx++; showPhase1()">السؤال التالي</button>
                    <button style="background:#636e72; font-size:14px;" onclick="startVoting()">إنهاء الجولة والتصويت</button>
                </div>`;
        }

        function showPhase2(asker, last = "") {
            document.getElementById('main-ui').innerHTML = `
                <div class="card"><span class="q-badge" style="background:var(--primary)">مرحلة الاختيار الحر</span>
                    <h3>دور <b style="color:var(--accent)">${asker}</b> يختار مين يسأل؟</h3>
                    <p style="font-size:13px; color:#bdc3c7;">ممنوع تسأل اللي سألك (${last || '---'})</p>
                    <div id="plist"></div>
                    <button style="margin-top:20px; background:#636e72" onclick="startVoting()">بدء التصويت</button>
                </div>`;
            game.players.forEach(p => {
                if(p!==asker && p!==last)
                    document.getElementById('plist').innerHTML += `<button class="vote-item" onclick="showPhase2('${p}', '${asker}')">اسأل ${p}</button>`;
            });
        }

        function startVoting() { p_votes = {}; performVote(0); }

        function performVote(idx) {
            if(idx >= game.players.length) { showReveal(); return; }
            let list = [...game.players].sort(() => Math.random() - 0.5);
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <p>مرر الجهاز لـ</p><h3>${game.players[idx]}</h3>
                    <p style="font-size:14px">صوت سراً: منو اللي برة السالفة؟</p>
                    <div id="vbox"></div>
                </div>`;
            list.forEach(p => {
                let btn = document.createElement('button');
                btn.className = 'vote-item'; btn.innerText = p;
                btn.onclick = () => { p_votes[game.players[idx]] = p; performVote(idx+1); };
                document.getElementById('vbox').appendChild(btn);
            });
        }

        function showReveal() {
            document.getElementById('main-ui').innerHTML = `<div class="card"><h1>جاري فرز الأصوات...</h1><div class="shuffling">🌀</div></div>`;
            setTimeout(() => {
                const spy = game.players[game.spy_idx];
                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h1>اللي برة السالفة كان:</h1>
                        <h2 style="color:var(--error); font-size:40px;">${spy}</h2>
                        <button onclick="spyGuess()">شاشة تخمين السالفة</button>
                    </div>`;
            }, 2000);
        }

        function spyGuess() {
            let h = `<h3>خمن وش السالفة؟ (فرصتك الأخيرة)</h3>`;
            game.guesses.forEach(g => h += `<div class="vote-item" onclick="finish('${g}')">${g}</div>`);
            document.getElementById('main-ui').innerHTML = `<div class="card">${h}</div>`;
        }

        function finish(g) {
            const win = (g === game.word);
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h1>${win ? '🎉 مبروك! الجاسوس فاز' : '🔥 خسر الجاسوس!'}</h1>
                    <p>السالفة كانت: <b>${game.word}</b></p>
                    <button onclick="showMenu()">جولة جديدة</button>
                </div>`;
        }

        function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }
        function updateSidebar() { if(currentUser) document.getElementById('user-display').innerText = currentUser.player_name; }
        function logout() { localStorage.clear(); location.reload(); }
        init();
    </script>
</body>
</html>
"""
