from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import json
import random
import os

# 1. THE APP INSTANCE - MUST be at the top level
app = FastAPI()

# 2. Game Logic Data
CATEGORIES = {
    "ألعاب": ["ببجي", "فيفا", "ماينكرافت", "قراند", "فورتنايت"],
    "حيوانات": ["أسد", "فيل", "زرافة", "نمر", "دب"],
    "أكلات": ["بيتزا", "برجر", "شاورما", "منسف", "كبسة"],
    "كرة قدم": ["ميسي", "رونالدو", "صلاح", "نيمار", "مبابي"]
}

# 3. Routes
@app.get("/", response_class=HTMLResponse)
async def home():
    cat_json = json.dumps(list(CATEGORIES.keys()), ensure_ascii=False)
    return HTML_TEMPLATE.replace("CAT_JSON_DATA", cat_json)

@app.post("/api/start")
async def start_api(data: dict):
    players = data.get('players', ["لاعب 1", "لاعب 2", "لاعب 3"])
    category = data.get('category', 'أكلات')
    word = random.choice(CATEGORIES.get(category, ["بيتزا"]))
    roles = ["in"] * len(players)
    roles[random.randint(0, len(players)-1)] = "spy"
    return {"players": players, "word": word, "roles": roles}

@app.post("/api/user/register")
async def register(data: dict):
    try:
        import psycopg2
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            with psycopg2.connect(db_url, sslmode='require') as conn:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO users (player_name, is_registered) VALUES (%s, %s)",
                                (data.get("name"), True))
                    conn.commit()
    except:
        pass
    return {"success": True}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>برا السالفة | Bara Alsalfa</title>
    <style>
        body { font-family: sans-serif; background: #f0f2f5; text-align: center; padding: 20px; direction: rtl; }
        .card { background: white; padding: 30px; border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 400px; margin: auto; }
        button { width: 100%; padding: 15px; margin: 10px 0; border-radius: 12px; border: none; background: #6c5ce7; color: white; font-weight: bold; cursor: pointer; }
        input { width: 100%; padding: 12px; margin: 8px 0; border-radius: 10px; border: 1px solid #ddd; box-sizing: border-box; }
        .word { font-size: 24px; color: #d93025; font-weight: bold; margin: 20px 0; display: none; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div id="app">
        <div class="card">
            <h1>🕵️ برا السالفة</h1>
            <p>لعبة الذكاء والخداع (أوفلاين)</p>
            <button onclick="startSetup()">ابدأ اللعب الآن</button>
        </div>
    </div>
    <script>
        const cats = CAT_JSON_DATA;
        let game = null;

        function startSetup() {
            document.getElementById('app').innerHTML = `
                <div class="card">
                    <h2>إعداد اللاعبين</h2>
                    <input class="p-in" value="لاعب 1">
                    <input class="p-in" value="لاعب 2">
                    <input class="p-in" value="لاعب 3">
                    <button onclick="startGame()">ابدأ</button>
                </div>`;
        }

        async function startGame() {
            const players = Array.from(document.querySelectorAll('.p-in')).map(i => i.value);
            const res = await fetch('/api/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({players})
            });
            game = await res.json();
            game.idx = 0;
            showTurn();
        }

        function showTurn() {
            if (game.idx >= game.players.length) {
                document.getElementById('app').innerHTML = '<div class="card"><h2>بدأ النقاش!</h2><button onclick="location.reload()">جولة جديدة</button></div>';
                return;
            }
            document.getElementById('app').innerHTML = `
                <div class="card">
                    <p>مرر الجهاز لـ</p>
                    <h3>${game.players[game.idx]}</h3>
                    <div id="wd" class="word"></div>
                    <button id="br" onclick="reveal()">اكشف السالفة</button>
                    <button id="bn" class="hidden" onclick="nextP()">التالي</button>
                </div>`;
        }

        function reveal() {
            const box = document.getElementById('wd');
            box.innerText = game.roles[game.idx] === 'spy' ? '🕵️ أنت برا السالفة!' : '🤫 السالفة: ' + game.word;
            box.style.display = 'block';
            document.getElementById('br').classList.add('hidden');
            document.getElementById('bn').classList.remove('hidden');
        }

        function nextP() { game.idx++; showTurn(); }
    </script>
</body>
</html>
"""
