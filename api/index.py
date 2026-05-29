import os
import sys
import time
import base64
from fastapi import FastAPI, Request, Response, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse

# 1. إعداد المسارات لضمان عمل الموديولات المحلية في Vercel
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# 2. تعريف التطبيق - هذا هو الكائن الذي يبحث عنه Vercel
app = FastAPI()
handler = app
application = app

# 3. استيراد الموديلات بشكل آمن (Lazy Imports)
modules_status = {"domino": False, "spy": False}
try:
    import domino
    app.include_router(domino.router)
    modules_status["domino"] = True
except Exception as e:
    print(f"Lazy import error (domino): {e}")

try:
    import spy
    app.include_router(spy.router)
    modules_status["spy"] = True
except Exception as e:
    print(f"Lazy import error (spy): {e}")

# --- المسارات (Routes) ---

@app.get("/api/health")
async def health():
    return {"status": "ok", "modules": modules_status}

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

@app.get("/api/admin/feedback")
async def get_feedback_api():
    try:
        from database import get_db, RealDictCursor
        with get_db() as conn:
            if not conn: return []
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM feedback ORDER BY created_at DESC LIMIT 100")
                return cur.fetchall()
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/feedback/delete")
async def delete_feedback_api(data: dict):
    try:
        from database import get_db
        with get_db() as conn:
            if not conn: return {"success": False}
            with conn.cursor() as cur:
                cur.execute("DELETE FROM feedback WHERE id = %s", (data['id'],))
                conn.commit()
            return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/room/{room_code}")
async def get_room_state(room_code: str):
    try:
        from database import get_db, RealDictCursor
        import json
        with get_db() as conn:
            if not conn: return {"success": False, "msg": "DB Connection Error"}
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM rooms WHERE room_code = %s", (room_code.upper(),))
                room = cur.fetchone()
                if not room: return {"success": False, "msg": "الغرفة غير موجودة"}
                if room.get('game_data') and isinstance(room['game_data'], str):
                    try: room['game_data'] = json.loads(room['game_data'])
                    except: pass

                # تحديث تلقائي للحالات في لعبة "برا السالفة" عند انتهاء الوقت
                if room.get('game_type') == 'spy' and room.get('game_data'):
                    gd = room['game_data']
                    ps = gd.get('phase_start')
                    if ps and (time.time() - ps > 60): # مهلة دقيقة واحدة لكل مرحلة مثلاً
                        from spy import calculate_online_results
                        changed = False
                        if room['status'] == 'voting_spy':
                            await calculate_online_results(room_code.upper(), conn=conn)
                            changed = True

                        if changed:
                            with conn.cursor(cursor_factory=RealDictCursor) as cur2:
                                cur2.execute("SELECT * FROM rooms WHERE room_code = %s", (room_code.upper(),))
                                room = cur2.fetchone()
                                if room.get('game_data') and isinstance(room['game_data'], str):
                                    room['game_data'] = json.loads(room['game_data'])

                cur.execute("SELECT user_id, player_name, team, score, is_ready, join_order, red_card FROM room_players WHERE room_code = %s ORDER BY join_order", (room_code.upper(),))
                players = cur.fetchall()
                return {"success": True, "room": room, "players": players}
    except Exception as e: return {"success": False, "error": str(e)}

# --- واجهة المستخدم الاحترافية ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>أونو وبرا السالفة</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root {
            --primary: #6c5ce7; --secondary: #00d2ff; --bg: #0f0c29;
            --card: rgba(255, 255, 255, 0.05); --accent: #00ff88;
            --error: #ff2d55; --text: #ffffff; --sidebar-w: 260px;
        }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body {
            font-family: 'Cairo', sans-serif; background: var(--bg); color: var(--text);
            margin: 0; display: flex; min-height: 100vh; overflow-x: hidden;
        }

        /* Sidebar */
        .sidebar {
            width: var(--sidebar-w); background: rgba(0,0,0,0.3); backdrop-filter: blur(20px);
            border-left: 1px solid rgba(255,255,255,0.1); display: flex; flex-direction: column;
            transition: 0.3s; position: fixed; height: 100vh; right: -260px; z-index: 1000;
        }
        .sidebar.active { right: 0; }
        .sidebar-header { padding: 20px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .sidebar-menu { flex: 1; padding: 10px; }
        .menu-item {
            padding: 15px; border-radius: 12px; display: flex; align-items: center; gap: 10px;
            cursor: pointer; transition: 0.2s; color: #ccc; margin-bottom: 5px;
        }
        .menu-item:hover { background: rgba(255,255,255,0.1); color: white; }
        .menu-item i { width: 20px; text-align: center; }

        /* Main Content */
        .main-content { flex: 1; display: flex; flex-direction: column; align-items: center; padding: 20px; transition: 0.3s; width: 100%; }
        .top-bar { width: 100%; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .menu-toggle { font-size: 1.5rem; cursor: pointer; padding: 10px; }

        .container { width: 100%; max-width: 500px; }
        .card {
            background: var(--card); backdrop-filter: blur(15px); padding: 30px;
            border-radius: 30px; border: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0 20px 50px rgba(0,0,0,0.3); text-align: center;
        }

        h1 { font-weight: 900; background: linear-gradient(to left, #00d2ff, #92fe9d); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; }

        .menu-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 25px 0; }
        .game-btn {
            background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
            border-radius: 20px; padding: 20px 10px; cursor: pointer; transition: 0.3s;
            display: flex; flex-direction: column; align-items: center; gap: 10px;
        }
        .game-btn:hover { background: rgba(255,255,255,0.1); transform: translateY(-5px); border-color: var(--secondary); }
        .game-btn i { font-size: 2rem; color: var(--secondary); }
        .game-btn.locked { opacity: 0.5; cursor: not-allowed; }

        input {
            width: 100%; padding: 15px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1);
            background: rgba(0,0,0,0.3); color: white; text-align: center; font-size: 1rem; margin-bottom: 10px;
        }

        .main-button {
            background: linear-gradient(45deg, var(--primary), var(--secondary)); color: white;
            border: none; padding: 15px; border-radius: 15px; width: 100%; font-size: 1.1rem;
            font-weight: bold; cursor: pointer; box-shadow: 0 10px 20px rgba(108,92,231,0.2); transition: 0.3s;
        }
        .main-button:active { transform: scale(0.98); }

        .secondary-button {
            background: transparent; border: 1px solid rgba(255,255,255,0.2); color: white;
            padding: 12px; border-radius: 15px; width: 100%; margin-top: 10px; cursor: pointer;
        }

        /* Toast Notification */
        #toast-container { position: fixed; top: 20px; left: 50%; transform: translateX(-50%); z-index: 2000; width: 90%; max-width: 400px; }
        .toast {
            background: rgba(0,0,0,0.8); backdrop-filter: blur(10px); color: white; padding: 15px 20px;
            border-radius: 12px; margin-bottom: 10px; border-right: 4px solid var(--primary);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3); animation: slideDown 0.3s ease;
        }
        @keyframes slideDown { from { transform: translateY(-20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

        /* Domino Board Styles */
        .domino-board { background: #1a472a; border-radius: 20px; min-height: 180px; margin: 20px 0; padding: 15px; display: flex; align-items: center; justify-content: center; overflow-x: auto; gap: 5px; }
        .tile {
            width: 35px; height: 70px; background: #f0f0f0; border-radius: 4px; color: #222;
            display: flex; flex-direction: column; border: 2px solid #333; flex-shrink: 0; cursor: pointer;
        }
        .tile.horizontal { width: 70px; height: 35px; flex-direction: row; }
        .tile .half { flex: 1; display: flex; justify-content: center; align-items: center; font-weight: 900; font-size: 1.2rem; border: 0.5px solid #ddd; }

        .loading-overlay { position: fixed; inset: 0; background: rgba(15,12,41,0.8); display: none; justify-content: center; align-items: center; z-index: 3000; }
        .spinner { width: 40px; height: 40px; border: 4px solid rgba(255,255,255,0.1); border-top-color: var(--secondary); border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="loading-overlay" id="loader"><div class="spinner"></div></div>
    <div id="toast-container"></div>

    <aside class="sidebar" id="sidebar">
        <div class="sidebar-header"><h3>الإعدادات</h3></div>
        <div class="sidebar-menu">
            <div class="menu-item" onclick="showAdmin()"><i class="fas fa-tools"></i> لوحة الإدارة</div>
            <div class="menu-item" onclick="location.reload()"><i class="fas fa-home"></i> الرئيسية</div>
            <div class="menu-item" onclick="showToast('قريباً...', 'info')"><i class="fas fa-user-circle"></i> الملف الشخصي</div>
            <div class="menu-item" onclick="showToast('شكراً لتواصلك معنا!', 'success')"><i class="fas fa-comment-dots"></i> أرسل اقتراحاً</div>
        </div>
    </aside>

    <main class="main-content">
        <div class="top-bar">
            <div class="menu-toggle" onclick="toggleSidebar()"><i class="fas fa-bars"></i></div>
            <h1 style="font-size: 1.2rem;">أونو وبرا السالفة</h1>
            <div style="width: 40px;"></div>
        </div>

        <div class="container" id="app-container">
            <div class="card" id="app">
                <h1>أونو وبرا السالفة</h1>
                <p style="color: #aaa; margin-top: 5px;">الجيل الجديد من الألعاب الجماعية</p>

                <div class="menu-grid">
                    <div class="game-btn" onclick="initGame('domino')">
                        <i class="fas fa-th-large"></i>
                        <span>دومينو</span>
                    </div>
                    <div class="game-btn" onclick="initGame('spy')">
                        <i class="fas fa-user-secret"></i>
                        <span>برا السالفة</span>
                    </div>
                    <div class="game-btn locked" onclick="showToast('قريباً جداً!', 'info')">
                        <i class="fas fa-layer-group"></i>
                        <span>أونو</span>
                    </div>
                    <div class="game-btn locked" onclick="showToast('قريباً!', 'info')">
                        <i class="fas fa-dice"></i>
                        <span>لودو</span>
                    </div>
                </div>

                <input type="text" id="player-name" placeholder="ادخل اسمك هنا..." value="لاعب محترف">
                <input type="text" id="room-code-input" placeholder="كود الغرفة (للانضمام)">

                <button class="main-button" style="margin-top: 10px;" onclick="joinRoom()">انضمام الآن</button>
            </div>
        </div>
    </main>

    <script>
        let currentUser = { id: Math.floor(100000 + Math.random() * 900000), name: "لاعب" };
        let currentRoom = null;
        let pollInterval = null;

        function toggleSidebar() { document.getElementById('sidebar').classList.toggle('active'); }

        function showToast(msg, type='info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.style.borderRightColor = type === 'error' ? 'var(--error)' : (type === 'success' ? 'var(--accent)' : 'var(--primary)');
            toast.innerHTML = msg;
            container.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);
        }

        function showLoader(v) { document.getElementById('loader').style.display = v ? 'flex' : 'none'; }

        async function apiCall(url, body) {
            showLoader(true);
            try {
                const res = await fetch(url, {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(body)
                });
                const data = await res.json();
                if(!data.success) showToast(data.msg || 'حدث خطأ غير متوقع', 'error');
                return data;
            } catch(e) {
                showToast('فشل الاتصال بالخادم', 'error');
                return {success: false};
            } finally { showLoader(false); }
        }

        function initGame(type) {
            currentUser.name = document.getElementById('player-name').value || "لاعب";
            if(type === 'domino') createRoom('/api/domino/create');
            else if(type === 'spy') createRoom('/api/online/create');
        }

        async function createRoom(url) {
            const data = await apiCall(url, { user_id: currentUser.id, player_name: currentUser.name });
            if(data.success) enterRoom(data.room_code);
        }

        async function joinRoom() {
            const code = document.getElementById('room-code-input').value.toUpperCase();
            if(!code) return showToast('برجاء إدخال كود الغرفة', 'error');
            const data = await apiCall('/api/online/join', { room_code: code, user_id: currentUser.id, player_name: document.getElementById('player-name').value });
            if(data.success) enterRoom(code);
        }

        function enterRoom(code) {
            currentRoom = code;
            document.getElementById('app').innerHTML = `<div style="padding: 40px;"><div class="spinner" style="margin: 0 auto;"></div><p style="margin-top:20px;">جاري دخول الغرفة ${code}...</p></div>`;
            if(pollInterval) clearInterval(pollInterval);
            pollInterval = setInterval(updateRoomState, 2000);
            updateRoomState();
        }

        async function updateRoomState() {
            if(!currentRoom) return;
            try {
                const res = await fetch(`/api/room/${currentRoom}`);
                const data = await res.json();
                if(data.success) renderRoom(data.room, data.players);
                else { clearInterval(pollInterval); currentRoom = null; location.reload(); }
            } catch(e) {}
        }

        function renderRoom(room, players) {
            let h = `<h2>غرفة ${room.game_type === 'domino' ? 'دومينو' : 'برا السالفة'}</h2>`;
            h += `<div style="background:rgba(255,255,255,0.1); padding:15px; border-radius:15px; margin-bottom:20px;">
                    <span style="font-size:1.8rem; font-weight:900; letter-spacing:8px; color:var(--secondary);">${room.room_code}</span>
                    <p style="margin:5px 0 0; font-size:0.8rem; color:#888;">شارك الكود مع أصدقائك</p>
                  </div>`;

            if(room.status === 'lobby' || room.status === 'waiting') {
                h += `<div style="text-align:right; margin-bottom:20px;"><h3 style="font-size:1rem; border-right:3px solid var(--secondary); padding-right:10px;">اللاعبون المتصلون (${players.length})</h3>`;
                players.forEach(p => {
                    const isMe = p.user_id == currentUser.id;
                    h += `<div style="padding:12px; background:rgba(255,255,255,0.03); border-radius:12px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
                            <span>${p.player_name} ${isMe ? '<small>(أنت)</small>' : ''}</span>
                            ${room.game_type === 'domino' ? `
                                <select onchange="setTeam('${room.room_code}', ${p.user_id}, this.value)" ${!isMe && room.host_id != currentUser.id ? 'disabled' : ''} style="background:#222; color:var(--secondary); border:1px solid #444; border-radius:8px; padding:4px 8px;">
                                    <option value="0" ${p.team == 0 ? 'selected' : ''}>فريق A</option>
                                    <option value="1" ${p.team == 1 ? 'selected' : ''}>فريق B</option>
                                </select>` : `<span style="color:var(--accent)"><i class="fas fa-check-circle"></i> جاهز</span>`}
                          </div>`;
                });
                h += `</div>`;

                if(room.game_type === 'spy') {
                    h += `<div style="margin-bottom:20px; text-align:right;">
                            <label style="display:block; margin-bottom:10px; font-size:0.9rem; color:#aaa;">اختر الفئة:</label>
                            <select id="spy-cat" style="width:100%; background:#222; color:white; border:1px solid #444; padding:10px; border-radius:12px;">
                                <option value="أكلات">أكلات</option>
                                <option value="أماكن">أماكن</option>
                                <option value="أدوات">أدوات</option>
                                <option value="رياضة">رياضة</option>
                            </select>
                          </div>`;
                }

                if(room.host_id == currentUser.id) h += `<button class="main-button" onclick="startGame('${room.game_type}')">ابدأ اللعبة الآن</button>`;
                else h += `<div style="padding:20px; color:#aaa;"><i class="fas fa-hourglass-half"></i> في انتظار المضيف...</div>`;
            } else if(room.game_type === 'domino') {
                h = renderDominoGame(room, players);
            } else if(room.game_type === 'spy') {
                h = renderSpyGame(room, players);
            } else {
                h += `<div style="padding:40px; color:var(--accent);"><i class="fas fa-play-circle fa-3x"></i><p>اللعبة جارية...</p></div>`;
            }

            h += `<button class="secondary-button" onclick="location.reload()">خروج من الغرفة</button>`;
            document.getElementById('app').innerHTML = h;
        }

        function renderSpyGame(room, players) {
            const gd = room.game_data;
            if(!gd) return '<h3>خطأ في تحميل البيانات</h3>';
            const isMeSpy = room.spy_id == currentUser.id;
            const myPlayer = players.find(p => p.user_id == currentUser.id);

            let h = `<div style="display:flex; justify-content:space-between; margin-bottom:15px; background:rgba(0,0,0,0.2); padding:10px; border-radius:12px;">
                        <div style="color:var(--secondary);">الفئة: ${room.category}</div>
                        <div style="color:var(--accent);">نقاطك: ${myPlayer?.score || 0} / ${room.win_limit}</div>
                     </div>`;

            if(room.status === 'roles_prep') {
                h += `<div class="card" style="background:rgba(255,255,255,0.05); border:2px dashed var(--primary);">
                        <h3>دورك في اللعبة</h3>
                        <div style="font-size:2rem; margin:20px 0; color:var(--accent);">
                            ${isMeSpy ? '<i class="fas fa-user-secret"></i> أنت برا السالفة!' : `<i class="fas fa-eye"></i> السالفة هي: ${room.secret_word}`}
                        </div>
                        <p style="color:#aaa;">تذكر الكلمة جيداً ولا تدع أحداً يعرف دورك</p>
                        ${myPlayer?.is_ready ? '<p style="color:var(--accent)">تم التأكيد، بانتظار البقية...</p>' : `<button class="main-button" onclick="apiCall('/api/online/action', {room_code:currentRoom, user_id:currentUser.id, action:'ready_role'})">فهمت!</button>`}
                      </div>`;
            } else if(room.status === 'playing_questions') {
                const cq = gd.current_q;
                if(!cq) {
                    const isMyTurnToAsk = gd.current_asker_id == currentUser.id;
                    h += `<div style="padding:20px; background:rgba(255,255,255,0.03); border-radius:20px;">
                            <h3>${isMyTurnToAsk ? 'دورك لتسأل!' : `في انتظار ${gd.current_asker_name} يختار من يسأل...`}</h3>
                            ${isMyTurnToAsk ? `
                                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:20px;">
                                    ${players.filter(p => p.user_id != currentUser.id).map(p => `
                                        <button class="game-btn" style="padding:10px;" onclick="apiCall('/api/online/action', {room_code:currentRoom, user_id:currentUser.id, action:'choose_target', target_id:${p.user_id}, target_name:'${p.player_name}'})">
                                            <span>${p.player_name}</span>
                                        </button>
                                    `).join('')}
                                </div>
                                <button class="secondary-button" style="margin-top:20px; border-color:var(--error); color:var(--error);" onclick="apiCall('/api/online/action', {room_code:currentRoom, user_id:currentUser.id, action:'start_voting'})">بدء التصويت النهائي</button>
                            ` : ''}
                          </div>`;
                } else if(cq.status === 'asking') {
                    const isMeAsker = cq.asker_id == currentUser.id;
                    h += `<div class="card">
                            <h3>${isMeAsker ? `اسأل ${cq.ans_name}` : `${players.find(p=>p.user_id==cq.asker_id)?.player_name} يسأل ${cq.ans_name}...`}</h3>
                            ${isMeAsker ? `
                                <input type="text" id="q-input" placeholder="اكتب سؤالك هنا..." style="margin-top:20px;">
                                <button class="main-button" onclick="apiCall('/api/online/action', {room_code:currentRoom, user_id:currentUser.id, action:'submit_question', text:document.getElementById('q-input').value})">إرسال السؤال</button>
                            ` : '<div class="spinner" style="margin:20px auto;"></div>'}
                          </div>`;
                } else if(cq.status === 'answering') {
                    const isMeAnswere = cq.ans_id == currentUser.id;
                    h += `<div class="card">
                            <p style="font-size:1.2rem; color:var(--secondary);">سؤال: ${cq.question}</p>
                            <h3>${isMeAnswere ? 'أجب على السؤال' : `في انتظار إجابة ${cq.ans_name}...`}</h3>
                            ${isMeAnswere ? `
                                <input type="text" id="a-input" placeholder="اكتب إجابتك هنا..." style="margin-top:20px;">
                                <button class="main-button" onclick="apiCall('/api/online/action', {room_code:currentRoom, user_id:currentUser.id, action:'submit_answer', text:document.getElementById('a-input').value})">إرسال الإجابة</button>
                            ` : '<div class="spinner" style="margin:20px auto;"></div>'}
                          </div>`;
                }

                if(gd.q_seq && gd.q_seq.length > 0) {
                    h += `<div style="margin-top:20px; text-align:right;">
                            <h4 style="border-bottom:1px solid #444; padding-bottom:5px;">سجل الأسئلة:</h4>
                            <div style="max-height:150px; overflow-y:auto; font-size:0.9rem;">
                                ${gd.q_seq.slice().reverse().map(q => `
                                    <div style="margin-bottom:10px; padding:8px; background:rgba(255,255,255,0.02); border-radius:8px;">
                                        <div style="color:var(--secondary);">${players.find(p=>p.user_id==q.asker_id)?.player_name} ⬅️ ${q.ans_name}</div>
                                        <div style="color:#fff;">س: ${q.question}</div>
                                        <div style="color:var(--accent);">ج: ${q.answer}</div>
                                    </div>
                                `).join('')}
                            </div>
                          </div>`;
                }
            } else if(room.status === 'voting_spy') {
                h += `<div class="card">
                        <h3>من هو "برا السالفة"؟</h3>
                        <p style="color:#aaa;">صوّت للشخص الذي تعتقد أنه لا يعرف الكلمة</p>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:20px;">
                            ${players.map(p => {
                                const isVoted = gd.votes && gd.votes[currentUser.id] == p.user_id;
                                return `<button class="game-btn" style="${isVoted ? 'border-color:var(--accent); background:rgba(0,255,136,0.1);' : ''}" onclick="apiCall('/api/online/action', {room_code:currentRoom, user_id:currentUser.id, action:'vote', target_id:${p.user_id}})">
                                            <span>${p.player_name}</span>
                                            ${isVoted ? '<i class="fas fa-check-circle" style="color:var(--accent)"></i>' : ''}
                                        </button>`;
                            }).join('')}
                        </div>
                      </div>`;
            } else if(room.status === 'spy_reveal' || room.status === 'result') {
                const spy = players.find(p => p.user_id == room.spy_id);
                const spyCaught = gd.spy_caught;
                h += `<div class="card">
                        <h2 style="color:${spyCaught ? 'var(--accent)' : 'var(--error)'}">${spyCaught ? '🎉 تم كشف الجاسوس!' : '😈 فاز الجاسوس!'}</h2>
                        <div style="margin:20px 0;">
                            <p style="font-size:1.2rem;">الجاسوس هو: <span style="color:var(--secondary); font-weight:bold;">${spy?.player_name}</span></p>
                            <p>الكلمة كانت: <span style="color:var(--accent);">${room.secret_word}</span></p>
                        </div>`;

                if(isMeSpy && !gd.game_over) {
                    h += `<div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:15px; margin-top:15px;">
                            <p>حاول تخمين الكلمة لتربح نقطة إضافية:</p>
                            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
                                ${gd.guesses.map(g => `<button class="secondary-button" style="margin:0; padding:8px;" onclick="apiCall('/api/online/action', {room_code:currentRoom, user_id:currentUser.id, action:'spy_guess', guess:'${g}'})">${g}</button>`).join('')}
                            </div>
                          </div>`;
                }

                if(gd.game_over) {
                    const winner = players.find(p => p.user_id == gd.winner_id);
                    h += `<div style="margin-top:20px; padding:20px; background:linear-gradient(45deg, #ffd700, #ffa500); border-radius:20px; color:#000;">
                            <i class="fas fa-crown fa-2x"></i>
                            <h3>الفائز باللعبة: ${winner?.player_name}</h3>
                          </div>`;
                }

                if(room.host_id == currentUser.id) {
                    h += `<button class="main-button" style="margin-top:20px;" onclick="apiCall('/api/online/action', {room_code:currentRoom, user_id:currentUser.id, action:'new_round'})">جولة جديدة</button>`;
                }
                h += `</div>`;
            }
            return h;
        }

        async function setTeam(code, uid, team) {
            await fetch('/api/domino/set_team', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ room_code: code, user_id: uid, team: team }) });
        }

        async function startGame(type) {
            const endpoint = type === 'domino' ? '/api/domino/start' : '/api/online/start';
            const body = { room_code: currentRoom, user_id: currentUser.id };
            if(type === 'spy') body.category = document.getElementById('spy-cat')?.value || 'أكلات';
            const data = await apiCall(endpoint, body);
            if(!data.success) showToast(data.msg, 'error');
        }

        function renderDominoGame(room, players) {
            const gd = room.game_data;
            if(!gd) return '<h3>خطأ في تحميل البيانات</h3>';
            const myId = currentUser.id.toString();
            const isMyTurn = gd.ordered_ids[gd.turn_index] == myId;
            const myHand = gd.hands[myId] || [];

            let h = `<div style="display:flex; justify-content:space-between; margin-bottom:15px; background:rgba(0,0,0,0.2); padding:10px; border-radius:12px;">
                        <div style="color:var(--secondary); font-weight:bold;">A: ${gd.scores['0']}</div>
                        <div style="color:#aaa;">جولة ${gd.round_count}</div>
                        <div style="color:var(--accent); font-weight:bold;">B: ${gd.scores['1']}</div>
                     </div>`;

            if(gd.phase === 'round_end' || gd.phase === 'game_over') {
                h += `<div style="background:rgba(108,92,231,0.1); padding:20px; border-radius:20px; border:1px solid var(--primary); margin-bottom:15px;">
                        <h3 style="margin:0; color:var(--accent);">${gd.is_stalemate ? '🔒 قفلة (انتهى اللعب)' : '🎉 جولة رابحة!'}</h3>
                        <p style="margin:10px 0;">الفائز: فريق ${gd.round_winner_team === '0' ? 'A' : 'B'}</p>
                        <p style="font-size:1.5rem; font-weight:900;">+${gd.round_points}</p>
                        ${room.host_id == currentUser.id ? `<button class="main-button" onclick="apiCall('/api/domino/next_round', {room_code:currentRoom, user_id:currentUser.id})">الجولة التالية</button>` : ''}
                      </div>`;
            }

            h += `<div class="domino-board">`;
            if(!gd.board || gd.board.length === 0) h += `<p style="color:#4a6d54;">الساحة في انتظار أول قطعة...</p>`;
            else gd.board.forEach(t => h += `<div class="tile ${t[0] != t[1] ? 'horizontal' : ''}"><div class="half">${t[0]}</div><div class="half">${t[1]}</div></div>`);
            h += `</div>`;

            h += `<div style="margin-bottom:15px; color:${isMyTurn ? 'var(--accent)' : '#aaa'};">
                    ${isMyTurn ? '<i class="fas fa-star"></i> دورك الآن!' : `دور: ${players.find(p => p.user_id == gd.ordered_ids[gd.turn_index])?.player_name}`}
                  </div>`;

            h += `<div style="display:flex; overflow-x:auto; gap:8px; padding:10px; background:rgba(255,255,255,0.03); border-radius:15px; margin-bottom:15px;">`;
            myHand.forEach(t => {
                const canL = gd.board.length === 0 || t[0] === gd.board[0][0] || t[1] === gd.board[0][0];
                const canR = gd.board.length === 0 || t[0] === gd.board[gd.board.length-1][1] || t[1] === gd.board[gd.board.length-1][1];
                h += `<div class="tile" onclick="handlePlay(${JSON.stringify(t)}, ${canL}, ${canR})"><div class="half">${t[0]}</div><div class="half">${t[1]}</div></div>`;
            });
            h += `</div>`;

            if(isMyTurn) h += `<button class="secondary-button" onclick="apiCall('/api/domino/draw', {room_code:currentRoom, user_id:currentUser.id})"><i class="fas fa-plus-circle"></i> سحب قطعة (${gd.boneyard?.length || 0})</button>`;
            return h;
        }

        async function handlePlay(tile, canL, canR) {
            if(!canL && !canR) return showToast('لا يمكن لعب هذه القطعة!', 'error');
            let side = 'right';
            if(canL && canR && document.querySelectorAll('.domino-board .tile').length > 0) side = confirm('لعب على اليمين (Ok) أم اليسار (Cancel)؟') ? 'right' : 'left';
            else side = canL ? 'left' : 'right';
            apiCall('/api/domino/play', { room_code: currentRoom, user_id: currentUser.id, tile: tile, side: side });
        }

        async function showAdmin() {
            toggleSidebar();
            document.getElementById('app').innerHTML = `<h2>تحميل الآراء...</h2>`;
            const res = await fetch('/api/admin/feedback');
            const data = await res.json();
            let h = '<h2>لوحة الآراء</h2><div style="max-height:350px; overflow-y:auto; padding:5px;">';
            if(!data.length) h += '<p>لا توجد آراء</p>';
            else data.forEach(f => h += `<div style="background:rgba(255,255,255,0.05); padding:12px; border-radius:12px; margin-bottom:10px; text-align:right;"><small style="color:var(--secondary);">${f.player_name}</small><p style="margin:5px 0;">${f.message}</p><button onclick="delFb(${f.id})" style="color:var(--error); background:none; border:none; cursor:pointer;">حذف</button></div>`);
            h += '</div><button class="main-button" onclick="location.reload()">العودة</button>';
            document.getElementById('app').innerHTML = h;
        }

        async function delFb(id) { if(confirm('متأكد؟')) { await apiCall('/api/feedback/delete', {id}); showAdmin(); } }
    </script>
</body>
</html>
"""
