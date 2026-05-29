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
try:
    from domino import router as domino_router
    app.include_router(domino_router)
    from spy import router as spy_router
    app.include_router(spy_router)
except Exception as e:
    print(f"Lazy import error: {e}")

# --- المسارات (Routes) ---

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

@app.get("/api/app_icon.png")
async def get_app_icon():
    default_icon = "https://cdn-icons-png.flaticon.com/512/8030/8030198.png"
    try:
        from database import get_db_conn
        conn = get_db_conn()
        if conn:
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM settings WHERE key = 'app_icon_data'")
                row = cur.fetchone()
                if row and row[0]:
                    return Response(content=base64.b64decode(row[0]), media_type="image/png")
    except:
        pass
    return RedirectResponse(url=default_icon)

@app.get("/api/room/{room_code}")
async def get_room_state(room_code: str):
    """نقطة نهاية موحدة للحصول على حالة الغرفة (دومينو أو برا السالفة)"""
    try:
        from database import get_db, RealDictCursor
        import json
        with get_db() as conn:
            if not conn: return {"success": False, "msg": "DB Connection Error"}
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM rooms WHERE room_code = %s", (room_code.upper(),))
                room = cur.fetchone()
                if not room: return {"success": False, "msg": "الغرفة غير موجودة"}

                # التأكد من أن game_data بصيغة dict
                if room.get('game_data') and isinstance(room['game_data'], str):
                    try:
                        room['game_data'] = json.loads(room['game_data'])
                    except:
                        pass

                cur.execute("SELECT user_id, player_name, team, score, is_ready, join_order FROM room_players WHERE room_code = %s ORDER BY join_order", (room_code.upper(),))
                players = cur.fetchall()

                return {"success": True, "room": room, "players": players}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- واجهة المستخدم (HTML) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>أونو وبرا السالفة</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #6c5ce7;
            --secondary: #00d2ff;
            --bg: #0f0c29;
            --card: rgba(255, 255, 255, 0.05);
            --accent: #00ff88;
            --error: #ff2d55;
            --text: #ffffff;
        }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body {
            font-family: 'Cairo', sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: var(--text);
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            overflow-x: hidden;
        }
        .container { width: 95%; max-width: 500px; padding: 20px; }
        .card {
            background: var(--card);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            padding: 30px;
            border-radius: 30px;
            border: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0 20px 50px rgba(0,0,0,0.3);
            text-align: center;
            animation: fadeIn 0.5s ease-out;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }

        h1 { font-weight: 900; font-size: 2.5em; margin-bottom: 10px; background: linear-gradient(to right, #00d2ff, #92fe9d); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        p { color: #ccc; margin-bottom: 30px; }

        .menu-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }
        .game-btn {
            background: rgba(255,255,255,0.1);
            border: 2px solid transparent;
            border-radius: 20px;
            padding: 20px 10px;
            cursor: pointer;
            transition: 0.3s;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
        }
        .game-btn:hover { background: rgba(255,255,255,0.2); transform: scale(1.05); border-color: var(--secondary); }
        .game-btn i { font-size: 2.5em; }
        .game-btn span { font-weight: bold; }

        .main-button {
            background: linear-gradient(45deg, var(--primary), var(--secondary));
            color: white;
            border: none;
            padding: 15px;
            border-radius: 15px;
            width: 100%;
            font-size: 1.2em;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 10px 20px rgba(108, 92, 231, 0.3);
            margin-top: 10px;
        }
        .secondary-button {
            background: transparent;
            border: 2px solid rgba(255,255,255,0.2);
            color: white;
            padding: 12px;
            border-radius: 15px;
            width: 100%;
            margin-top: 10px;
            cursor: pointer;
            font-weight: bold;
        }

        input {
            width: 100%;
            padding: 15px;
            border-radius: 15px;
            border: 1px solid rgba(255,255,255,0.1);
            background: rgba(0,0,0,0.2);
            color: white;
            text-align: center;
            font-size: 1.1em;
            margin-bottom: 15px;
        }

        .admin-link { margin-top: 30px; display: block; color: #666; font-size: 0.8em; text-decoration: none; cursor: pointer; }

        /* Game Specific UI */
        .domino-board { background: #1a472a; border-radius: 20px; min-height: 200px; margin: 20px 0; padding: 10px; overflow-x: auto; white-space: nowrap; }
        .tile {
            display: inline-flex;
            flex-direction: column;
            width: 40px;
            height: 80px;
            background: white;
            border-radius: 5px;
            margin: 5px;
            color: black;
            border: 2px solid #333;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.5);
            position: relative;
        }
        .tile.horizontal { width: 80px; height: 40px; flex-direction: row; }
        .tile .half { flex: 1; display: flex; justify-content: center; align-items: center; font-weight: bold; font-size: 1.5em; border: 1px solid #eee; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card" id="app">
            <h1>أونو وبرا السالفة</h1>
            <p>اختر اللعبة وابدأ التحدي!</p>

            <div class="menu-grid">
                <div class="game-btn" onclick="initGame('domino')">
                    <i>🀄</i>
                    <span>دومينو</span>
                </div>
                <div class="game-btn" onclick="initGame('spy')">
                    <i>🕵️‍♂️</i>
                    <span>برا السالفة</span>
                </div>
                <div class="game-btn" onclick="alert('قريباً...')">
                    <i>🃏</i>
                    <span>أونو</span>
                </div>
                <div class="game-btn" onclick="alert('قريباً...')">
                    <i>🎲</i>
                    <span>لودو</span>
                </div>
            </div>

            <input type="text" id="player-name" placeholder="أدخل اسمك" value="لاعب">
            <input type="text" id="room-code-input" placeholder="كود الغرفة (للانضمام)">

            <button class="secondary-button" onclick="joinRoom()">انضمام لغرفة</button>

            <span class="admin-link" onclick="showAdmin()">🛠️ الإدارة</span>
        </div>
    </div>

    <script>
        let currentUser = { id: Math.floor(Math.random() * 1000000), name: "لاعب" };
        let currentRoom = null;
        let pollInterval = null;

        function initGame(type) {
            const name = document.getElementById('player-name').value || "لاعب";
            currentUser.name = name;
            if(type === 'domino') createDominoRoom();
            else if(type === 'spy') createSpyRoom();
        }

        async function createDominoRoom() {
            const res = await fetch('/api/domino/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: currentUser.id, player_name: currentUser.name })
            });
            const data = await res.json();
            if(data.success) enterRoom(data.room_code);
        }

        async function createSpyRoom() {
            const res = await fetch('/api/online/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: currentUser.id, player_name: currentUser.name })
            });
            const data = await res.json();
            if(data.success) enterRoom(data.room_code);
        }

        async function joinRoom() {
            const code = document.getElementById('room-code-input').value.toUpperCase();
            const name = document.getElementById('player-name').value || "لاعب";
            if(!code) return alert('أدخل الكود');

            const res = await fetch('/api/online/join', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ room_code: code, user_id: currentUser.id, player_name: name })
            });
            const data = await res.json();
            if(data.success) enterRoom(code);
            else alert(data.msg || 'فشل الانضمام');
        }

        function enterRoom(code) {
            currentRoom = code;
            document.getElementById('app').innerHTML = `<h2>جاري التحميل...</h2><p>كود الغرفة: ${code}</p>`;
            startPolling();
        }

        function startPolling() {
            if(pollInterval) clearInterval(pollInterval);
            pollInterval = setInterval(updateRoomState, 2000);
            updateRoomState();
        }

        async function updateRoomState() {
            if(!currentRoom) return;
            const res = await fetch(\`/api/room/\${currentRoom}\`);
            const data = await res.json();
            if(data.success) renderRoom(data.room, data.players);
        }

        function renderRoom(room, players) {
            let html = `<h2>غرفة ${room.game_type === 'domino' ? 'دومينو' : 'برا السالفة'}</h2>`;
            html += `<div style="background:rgba(255,255,255,0.1); padding:10px; border-radius:10px; margin-bottom:20px;">
                        <span style="font-size:1.5em; font-weight:bold; letter-spacing:5px;">${room.room_code}</span>
                      </div>`;

            if(room.status === 'lobby' || room.status === 'waiting') {
                html += `<div style="text-align:right; margin-bottom:20px;"><strong>اللاعبون:</strong><ul style="list-style:none; padding:0;">`;
                players.forEach(p => {
                    const isMe = p.user_id == currentUser.id;
                    html += `<li style="padding:10px; border-bottom:1px solid rgba(255,255,255,0.05); display:flex; justify-content:space-between; align-items:center;">
                                <span>${p.player_name} ${isMe ? '(أنت)' : ''}</span>
                                ${room.game_type === 'domino' ? `
                                    <select onchange="setTeam('${room.room_code}', ${p.user_id}, this.value)" ${!isMe && room.host_id != currentUser.id ? 'disabled' : ''} style="background:#333; color:white; border:none; border-radius:5px; padding:2px;">
                                        <option value="0" ${p.team == 0 ? 'selected' : ''}>فريق A</option>
                                        <option value="1" ${p.team == 1 ? 'selected' : ''}>فريق B</option>
                                    </select>
                                ` : ''}
                             </li>`;
                });
                html += `</ul></div>`;

                if(room.host_id == currentUser.id) {
                    html += `<button class="main-button" onclick="startGame('${room.game_type}')">ابدأ اللعبة</button>`;
                } else {
                    html += `<p class="animate-pulse">في انتظار المضيف لبدء اللعبة...</p>`;
                }
            } else if(room.game_type === 'domino') {
                html = renderDominoGame(room, players);
            } else {
                html += `<p>اللعبة جارية (برا السالفة)...</p>`;
            }

            html += `<button class="secondary-button" onclick="location.reload()" style="margin-top:20px;">خروج</button>`;
            document.getElementById('app').innerHTML = html;
        }

        async function setTeam(code, uid, team) {
            await fetch('/api/domino/set_team', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ room_code: code, user_id: uid, team: team })
            });
        }

        function renderDominoGame(room, players) {
            const gd = room.game_data;
            if(!gd) return '<h2>خطأ في البيانات</h2>';

            const myId = currentUser.id.toString();
            const isMyTurn = gd.ordered_ids[gd.turn_index] == myId;
            const myHand = gd.hands[myId] || [];

            let h = `<div style="display:flex; justify-content:space-between; margin-bottom:10px; font-size:0.9em;">
                        <div style="color:var(--secondary)">فريق A: ${gd.scores['0']}</div>
                        <div>الجولة: ${gd.round_count}</div>
                        <div style="color:var(--accent)">فريق B: ${gd.scores['1']}</div>
                     </div>`;

            if(gd.phase === 'round_end' || gd.phase === 'game_over') {
                h += `<div style="background:rgba(0,0,0,0.5); padding:20px; border-radius:15px; margin:20px 0; border:2px solid var(--accent);">
                        <h3>${gd.is_stalemate ? '🔒 قفلة!' : '🎉 انتهت الجولة!'}</h3>
                        <p>الفائز: فريق ${gd.round_winner_team === '0' ? 'A' : 'B'}</p>
                        <p>النقاط المحتسبة: ${gd.round_points}</p>
                        ${gd.phase === 'game_over' ? '<h2 style="color:var(--secondary)">🏆 الفوز النهائي!</h2>' :
                          (room.host_id == currentUser.id ? `<button class="main-button" onclick="nextRound()">جولة جديدة</button>` : '<p>في انتظار المضيف لبدء الجولة التالية...</p>')}
                      </div>`;
            }

            h += `<div class="domino-board">`;
            if(!gd.board || gd.board.length === 0) {
                h += `<p style="color:#666; margin-top:80px;">الساحة فارغة</p>`;
            } else {
                gd.board.forEach((t, i) => {
                    const isHorizontal = t[0] !== t[1];
                    h += `<div class="tile ${isHorizontal ? 'horizontal' : ''}">
                            <div class="half">${t[0]}</div>
                            <div class="half">${t[1]}</div>
                          </div>`;
                });
            }
            h += `</div>`;

            h += `<div style="margin:10px 0; color:${isMyTurn ? 'var(--accent)' : '#aaa'}; font-weight:bold;">
                    ${isMyTurn ? '👉 دورك الآن!' : `دور: ${players.find(p => p.user_id == gd.ordered_ids[gd.turn_index])?.player_name || '...'}`}
                  </div>`;

            h += `<div style="overflow-x:auto; white-space:nowrap; padding:10px 0; background:rgba(255,255,255,0.05); border-radius:15px;">`;
            myHand.forEach((t, idx) => {
                const canPlayLeft = gd.board.length === 0 || t[0] === gd.board[0][0] || t[1] === gd.board[0][0];
                const canPlayRight = gd.board.length === 0 || t[0] === gd.board[gd.board.length-1][1] || t[1] === gd.board[gd.board.length-1][1];

                h += `<div class="tile" onclick="showPlayOptions(${JSON.stringify(t)}, ${canPlayLeft}, ${canPlayRight})">
                        <div class="half">${t[0]}</div>
                        <div class="half">${t[1]}</div>
                      </div>`;
            });
            h += `</div>`;

            if(isMyTurn) {
                h += `<div style="display:flex; gap:10px; margin-top:10px;">
                        <button class="secondary-button" style="flex:1" onclick="drawTile()">سحب من السوق (${gd.boneyard?.length || 0})</button>
                      </div>`;
            }

            return h;
        }

        async function showPlayOptions(tile, left, right) {
            if(!left && !right) return alert('هذه القطعة لا يمكن لعبها حالياً');
            if(left && right && document.querySelectorAll('.domino-board .tile').length > 0) {
                const side = confirm('لعب على اليمين (Ok) أم اليسار (Cancel)؟') ? 'right' : 'left';
                playTile(tile, side);
            } else {
                playTile(tile, left ? 'left' : 'right');
            }
        }

        async function playTile(tile, side) {
            const res = await fetch('/api/domino/play', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ room_code: currentRoom, user_id: currentUser.id, tile: tile, side: side })
            });
            const data = await res.json();
            if(!data.success) alert(data.msg);
        }

        async function drawTile() {
            const res = await fetch('/api/domino/draw', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ room_code: currentRoom, user_id: currentUser.id })
            });
            const data = await res.json();
            if(!data.success) alert(data.msg);
        }

        async function nextRound() {
            await fetch('/api/domino/next_round', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ room_code: currentRoom, user_id: currentUser.id })
            });
        }

        async function startGame(type) {
            const endpoint = type === 'domino' ? '/api/domino/start' : '/api/online/start';
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ room_code: currentRoom, user_id: currentUser.id })
            });
            const data = await res.json();
            if(!data.success) alert(data.msg);
        }

        async function showAdmin() {
            document.getElementById('app').innerHTML = `
                <h2>لوحة التحكم</h2>
                <button class="main-button" onclick="manageFeedback()">💬 الآراء والشكاوى</button>
                <button class="secondary-button" onclick="location.reload()">🏠 العودة</button>
            `;
        }

        async function manageFeedback() {
            const res = await fetch('/api/admin/feedback');
            const data = await res.json();
            let h = '<h2>الآراء</h2><div style="max-height:400px; overflow-y:auto; margin-bottom:20px;">';
            if(data.error) h += `<p style="color:red">${data.error}</p>`;
            else if(!data.length) h += '<p>لا توجد آراء حالياً</p>';
            else data.forEach(f => {
                h += `<div style="background:rgba(255,255,255,0.05); padding:10px; margin:5px; border-radius:10px; text-align:right;">
                    <small style="color:var(--secondary)">${f.player_name || 'مجهول'}</small>
                    <p style="margin:5px 0;">${f.message || ''}</p>
                    <button onclick="delFb(${f.id})" style="background:var(--error); color:white; border:none; padding:5px 10px; border-radius:5px; font-size:0.8em; cursor:pointer;">حذف</button>
                </div>`;
            });
            h += '</div><button class="secondary-button" onclick="showAdmin()">رجوع</button>';
            document.getElementById('app').innerHTML = h;
        }

        async function delFb(id) {
            if(confirm('هل تريد حذف هذا الرأي؟')) {
                await fetch('/api/feedback/delete', {
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({id})
                });
                manageFeedback();
            }
        }
    </script>
</body>
</html>
"""

