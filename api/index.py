import os
import json
import random
from typing import List, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

# -----------------------------------------------------------------------------
# 1. الموديلات والبيانات
# -----------------------------------------------------------------------------
class StartGameRequest(BaseModel):
    players: List[str]
    category: str

# الفئات الافتراضية لعرضها فوراً قبل تحميل البيانات من السيرفر
DEFAULT_CAT_NAMES = ["عام", "فواكه", "حيوانات", "مشاهير", "دول", "رياضة"]

# قاعدة بيانات وهمية (يتم استبدالها ببيانات حقيقية من قاعدة بياناتك)
CATEGORIES_DB = {
    "عام": ["طائرة", "مدرسة", "مستشفى", "سيارة", "تلفزيون", "ساعة", "مفتاح"],
    "فواكه": ["تفاح", "موز", "مانجو", "فراولة", "عنب", "بطيخ", "برتقال"],
    "حيوانات": ["أسد", "فيل", "زرافة", "قطة", "كلب", "نمر", "ذئب"],
    "مشاهير": ["ميسي", "رونالدو", "محمد صلاح", "شاكيرا", "توم كروز", "ويل سميث"],
    "دول": ["السعودية", "مصر", "الكويت", "قطر", "العراق", "الأردن", "المغرب"],
    "رياضة": ["كرة القدم", "كرة السلة", "التنس", "السباحة", "الملاكمة", "الجودو"]
}

# روابط الصور (اختياري)
CATEGORIES_IMAGES = {
    "عام": "https://img.freepik.com/free-photo/abstract-surface-textures-white-concrete-wall_74190-8189.jpg",
    "فواكه": "https://img.freepik.com/free-photo/vivid-blurred-colorful-wallpaper-background_58702-8508.jpg",
    "حيوانات": "https://img.freepik.com/free-photo/wildlife-background-with-leopard_23-2150821040.jpg",
    "مشاهير": "https://img.freepik.com/free-photo/people-celebrating-red-carpet-event_23-2150165510.jpg",
    "دول": "https://img.freepik.com/free-vector/world-map-composed-dots-lines-global-business-concept_1017-14246.jpg",
    "رياضة": "https://img.freepik.com/free-photo/soccer-players-action-professional-stadium_654080-1134.jpg"
}

# -----------------------------------------------------------------------------
# 2. المسارات (API)
# -----------------------------------------------------------------------------
@app.get("/api/categories")
async def get_categories():
    return [{"name": name, "image_url": CATEGORIES_IMAGES.get(name)} for name in CATEGORIES_DB.keys()]

@app.post("/api/game/start")
async def start_game(req: StartGameRequest):
    if req.category not in CATEGORIES_DB:
        raise HTTPException(status_code=404, detail="Category not found")

    words = CATEGORIES_DB[req.category]
    word = random.choice(words)
    players = req.players
    random.shuffle(players)

    spy_idx = random.randint(0, len(players) - 1)
    roles = ["spy" if i == spy_idx else "player" for i in range(len(players))]

    # توليد تسلسل أسئلة عشوائي
    q_seq = []
    others = [p for p in players]
    for i in range(len(players)):
        asker = players[i]
        possible_targets = [p for p in players if p != asker]
        target = random.choice(possible_targets)
        q_seq.append({"f": asker, "t": target})

    return {
        "word": word,
        "spy_idx": spy_idx,
        "roles": roles,
        "q_seq": q_seq
    }

# -----------------------------------------------------------------------------
# 3. الواجهة الأمامية (HTML/JS/CSS)
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index():
    return """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>برا السالفة | المجلس</title>
    <style>
        :root {
            --bg: #0f0c29;
            --card: #1b1464;
            --accent: #ffeb3b;
            --text: #ffffff;
            --success: #00d2d3;
            --error: #ff7675;
            --primary: #6c5ce7;
        }

        * { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; -webkit-tap-highlight-color: transparent; }
        body { background: var(--bg); color: var(--text); margin: 0; display: flex; flex-direction: column; align-items: center; min-height: 100vh; overflow-x: hidden; }

        .card { background: var(--card); border-radius: 30px; padding: 25px; width: 90%; max-width: 450px; text-align: center; box-shadow: 0 15px 35px rgba(0,0,0,0.5); margin: 20px 0; border: 1px solid rgba(255,255,255,0.1); }

        button { background: var(--primary); color: white; border: none; padding: 15px 25px; border-radius: 15px; font-size: 18px; font-weight: bold; cursor: pointer; width: 100%; margin: 10px 0; transition: transform 0.1s, background 0.2s; }
        button:active { transform: scale(0.95); }
        .btn-yellow { background: var(--accent); color: #1b1464; }

        input { width: 100%; padding: 15px; border-radius: 12px; border: none; background: rgba(255,255,255,0.1); color: white; margin-bottom: 15px; font-size: 16px; text-align: center; }

        .cat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 15px 0; }
        .cat-card { background: #2f278c; padding: 10px; border-radius: 15px; cursor: pointer; border: 2px solid transparent; transition: 0.2s; position: relative; overflow: hidden; }
        .cat-card.selected { border-color: var(--accent); background: #3c339e; }
        .cat-card span { font-size: 12px; font-weight: bold; display: block; margin-top: 5px; }

        .shimmer { background: linear-gradient(90deg, #2f278c 25%, #3c339e 50%, #2f278c 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; position: absolute; top:0; left:0; width:100%; height:100%; z-index: 1; }
        @keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }

        .score-item { display: flex; justify-content: space-between; background: rgba(255,255,255,0.05); padding: 12px 20px; border-radius: 12px; margin-bottom: 8px; }
        .win-opt { width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; background: #2f278c; cursor: pointer; border: 2px solid transparent; }
        .win-opt.selected { background: var(--accent); color: #1b1464; font-weight: bold; border-color: white; }

        .vote-item { background: #2f278c; padding: 15px; border-radius: 12px; margin: 8px 0; cursor: pointer; width: 100%; text-align: center; font-weight: bold; border: 2px solid transparent; }

        .hidden { display: none !important; }
        .reveal-text { font-size: 24px; font-weight: 900; color: var(--accent); text-shadow: 0 0 10px rgba(255,235,59,0.3); }

        .shuffling { font-size: 60px; margin: 20px; animation: bounce 1s infinite; }
        @keyframes bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-20px); } }

        #global-exit-btn { position: fixed; top: 15px; left: 15px; width: 40px; height: 40px; border-radius: 50%; background: var(--error); z-index: 999; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px; }
    </style>
</head>
<body>

    <div id="global-exit-btn" class="hidden" onclick="location.reload()">X</div>

    <div id="main-ui" style="width: 100%; display: flex; flex-direction: column; align-items: center;">
        <div class="card" style="margin-top: 50px;">
            <h1 style="font-size: 40px; margin-bottom: 10px;">🕵️ برا السالفة</h1>
            <p style="color: #aaa; margin-bottom: 30px;">لعبة المجلس والذكاء</p>
            <button class="btn-yellow" onclick="showSetup(1)">ابدأ اللعبة</button>
            <button style="background: transparent; border: 1px solid #aaa;" onclick="alert('قريباً')">كيف تلعب؟</button>
        </div>
    </div>

    <script>
        let game = null;
        let currentUser = { saved_players: [] };
        let totalScores = {};
        let winLimit = 10;
        let questionTimeout = 60;
        let voteTimeout = 30;
        let timerInterval = null;
        let p_votes = {};

        const DEFAULT_CAT_NAMES = ["عام", "فواكه", "حيوانات", "مشاهير", "دول", "رياضة"];

        function playSound(type) {
            console.log("Sound:", type);
        }

        function showSetup(step) {
            if(step === 1) {
                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2>عدد اللاعبين؟</h2>
                        <div style="display: flex; align-items: center; justify-content: center; gap: 20px; margin: 30px 0;">
                            <button onclick="updatePCountInput(-1)" style="width: 60px; height: 60px; font-size: 30px; margin:0;">-</button>
                            <span id="p-count-display" style="font-size: 40px; font-weight: 900; color:var(--accent); min-width: 60px;">3</span>
                            <button onclick="updatePCountInput(1)" style="width: 60px; height: 60px; font-size: 30px; margin:0;">+</button>
                        </div>
                        <button class="btn-yellow" onclick="savePCountAndNext()">التالي</button>
                        <button style="background:#636e72" onclick="location.reload()">رجوع</button>
                    </div>`;
            } else if(step === 2) {
                const targetN = parseInt(localStorage.getItem('pCount') || 3);
                let savedPlayers = JSON.parse(localStorage.getItem('savedPlayers') || '[]');

                let h = `<div id="p_selection_list" style="max-height: 300px; overflow-y: auto; margin-bottom: 20px; text-align: right;">`;
                savedPlayers.forEach((p, idx) => {
                    h += `
                        <div class="score-item" style="cursor:pointer" onclick="togglePSelection(this, '${p.replace(/'/g, "\\'")}')">
                            <span>${p}</span>
                            <span class="status-icon">⬜</span>
                        </div>`;
                });
                h += `</div>`;

                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2>اختر اللاعبين</h2>
                        <div style="display:flex; gap:10px; margin-bottom:15px;">
                            <input id="new_p_name" placeholder="اسم لاعب جديد" style="margin:0">
                            <button onclick="addNewPlayerToList()" style="width:80px; margin:0; background:var(--success)">+</button>
                        </div>
                        ${h}
                        <p id="selection_info" style="margin:10px 0; font-size:16px;">
                            المختار: <span id="selected_count" style="color:var(--success); font-weight:bold;">0</span> من <span id="required_n_summary">${targetN}</span>
                        </p>
                        <button class="btn-yellow" onclick="confirmPlayersAndNext()">التالي</button>
                        <button style="background:#636e72" onclick="showSetup(1)">رجوع</button>
                    </div>`;
                updateSelectedCount();
            } else if(step === 3) {
                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2>اختر نوع السالفة</h2>
                        <div id="cats-container" class="cat-grid"></div>
                        <input type="hidden" id="selected_cat">

                        <p style="margin-top:20px; font-weight:bold;">حد الفوز:</p>
                        <div style="display: flex; gap: 10px; justify-content: center; margin-bottom: 20px;">
                            <div class="win-opt" onclick="selectWinLimit(this, 5)">5</div>
                            <div class="win-opt selected" onclick="selectWinLimit(this, 10)">10</div>
                            <div class="win-opt" onclick="selectWinLimit(this, 15)">15</div>
                        </div>
                        <input type="hidden" id="win_limit_val" value="10">

                        <button class="btn-yellow" id="start-btn" onclick="startGameFinal()">ابدأ اللعب</button>
                        <button style="background:#636e72" onclick="showSetup(2)">رجوع</button>
                    </div>`;

                renderCategories(DEFAULT_CAT_NAMES.map(name => ({name, image_url: null})));

                // جلب الفئات الحقيقية
                fetch('/api/categories').then(r => r.json()).then(cats => renderCategories(cats)).catch(e => console.log(e));
            }
        }

        function updatePCountInput(delta) {
            const el = document.getElementById('p-count-display');
            let val = parseInt(el.innerText) + delta;
            if(val < 3) val = 3; if(val > 10) val = 10;
            el.innerText = val;
        }

        function savePCountAndNext() {
            localStorage.setItem('pCount', document.getElementById('p-count-display').innerText);
            showSetup(2);
        }

        function togglePSelection(el, name) {
            el.classList.toggle('selected-p');
            el.querySelector('.status-icon').innerText = el.classList.contains('selected-p') ? '✅' : '⬜';
            updateSelectedCount();
        }

        function updateSelectedCount() {
            const selected = document.querySelectorAll('.selected-p').length;
            const target = parseInt(localStorage.getItem('pCount') || 3);
            const el = document.getElementById('selected_count');
            if(el) {
                el.innerText = selected;
                el.style.color = (selected === target) ? 'var(--success)' : 'var(--error)';
            }
        }

        function addNewPlayerToList() {
            const name = document.getElementById('new_p_name').value.trim();
            if(!name) return;
            let saved = JSON.parse(localStorage.getItem('savedPlayers') || '[]');
            if(!saved.includes(name)) {
                saved.push(name);
                localStorage.setItem('savedPlayers', JSON.stringify(saved));
            }
            document.getElementById('new_p_name').value = "";
            showSetup(2);
        }

        function confirmPlayersAndNext() {
            const selected = Array.from(document.querySelectorAll('.selected-p')).map(el => el.querySelector('span').innerText);
            const target = parseInt(localStorage.getItem('pCount') || 3);
            if(selected.length !== target) return alert(`يجب اختيار ${target} لاعبين بالضبط!`);
            window.pNamesSave = selected;
            showSetup(3);
        }

        function renderCategories(cats) {
            const container = document.getElementById('cats-container');
            if(!container) return;
            let h = "";
            cats.forEach(c => {
                h += `
                    <div class="cat-card" onclick="selectCat(this, '${c.name}')">
                        <div style="width:100%; height:50px; background:#2f278c; border-radius:10px; position:relative; overflow:hidden;">
                            ${c.image_url ? `<img src="${c.image_url}" style="width:100%; height:100%; object-fit:cover;">` : '<div class="shimmer"></div>'}
                        </div>
                        <span>${c.name}</span>
                    </div>`;
            });
            container.innerHTML = h;
        }

        function selectCat(el, name) {
            document.querySelectorAll('.cat-card').forEach(c => c.classList.remove('selected'));
            el.classList.add('selected');
            document.getElementById('selected_cat').value = name;
        }

        function selectWinLimit(el, val) {
            document.querySelectorAll('.win-opt').forEach(o => o.classList.remove('selected'));
            el.classList.add('selected');
            document.getElementById('win_limit_val').value = val;
        }

        function startGameFinal() {
            const cat = document.getElementById('selected_cat').value;
            if(!cat) return alert("اختر فئة!");

            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <div class="shuffling">🕵️</div>
                    <h2>جاري التجهيز...</h2>
                </div>`;

            start(cat);
        }

        async function start(category) {
            document.getElementById('global-exit-btn').classList.remove('hidden');
            const players = window.pNamesSave;

            try {
                const res = await fetch('/api/game/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({players, category})
                });
                game = await res.json();
                game.players = players;
                game.curr = 0;
                showRole();
            } catch(e) {
                alert("خطأ في الاتصال");
                location.reload();
            }
        }

        function showRole() {
            if(game.curr >= game.players.length) { showPhase1(); return; }
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <p>مرر الجهاز لـ</p><h2>${game.players[game.curr]}</h2>
                    <div id="box" class="hidden" style="background:#0f0c29; padding:20px; border-radius:15px; margin:20px 0;">
                        <h3 class="reveal-text">${game.roles[game.curr] === 'spy' ? '🕵️ أنت برة السالفة!' : '🤫 السالفة: ' + game.word}</h3>
                    </div>
                    <button onclick="document.getElementById('box').classList.remove('hidden'); this.style.display='none'; document.getElementById('bnxt').style.display='block'">اكشف الدور</button>
                    <button id="bnxt" style="display:none" onclick="game.curr++; showRole()">التالي</button>
                </div>`;
        }

        function showPhase1() {
            game.qIdx = game.qIdx || 0;
            if(game.qIdx >= game.q_seq.length) { startVoting(); return; }
            const q = game.q_seq[game.qIdx];
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h3>الأسئلة</h3>
                    <div style="font-size:22px; margin:30px 0;"><b>${q.f}</b> يسأل <b>${q.t}</b></div>
                    <button onclick="game.qIdx++; showPhase1()">السؤال التالي</button>
                    <button style="background:var(--accent); color:black" onclick="startVoting()">بدء التصويت</button>
                </div>`;
        }

        function startVoting() {
            p_votes = {};
            performVote(0);
        }

        function performVote(idx) {
            if(idx >= game.players.length) { showReveal(); return; }
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h3>دور ${game.players[idx]}</h3>
                    <p>صوت على اللي برة السالفة:</p>
                    <div id="vbox"></div>
                </div>`;
            game.players.forEach(p => {
                let b = document.createElement('button'); b.innerText = p; b.className = 'vote-item';
                b.onclick = () => { p_votes[game.players[idx]] = p; performVote(idx+1); };
                document.getElementById('vbox').appendChild(b);
            });
        }

        function showReveal() {
            const spy = game.players[game.spy_idx];
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>اللي كان برة السالفة هو:</h2>
                    <h1 class="reveal-text">${spy}</h1>
                    <button class="btn-yellow" onclick="location.reload()">لعبة جديدة</button>
                </div>`;
        }
    </script>
</body>
</html>
    """
