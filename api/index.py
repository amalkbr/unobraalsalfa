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
        try:
            conn = psycopg2.connect(db_url, sslmode='require')
            return conn
        except Exception as e:
            print(f"DB Error: {e}")
            return None
    return None

def init_db():
    conn = get_db_conn()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id SERIAL PRIMARY KEY,
                    username_key TEXT UNIQUE,
                    password_key TEXT,
                    player_name TEXT,
                    is_registered BOOLEAN DEFAULT FALSE
                );
                CREATE TABLE IF NOT EXISTS rooms (
                    room_code TEXT PRIMARY KEY,
                    host_id INTEGER,
                    status TEXT DEFAULT 'waiting',
                    category TEXT,
                    win_limit INTEGER DEFAULT 1000,
                    game_data JSONB,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS room_players (
                    room_code TEXT REFERENCES rooms(room_code) ON DELETE CASCADE,
                    user_id INTEGER,
                    player_name TEXT,
                    score INTEGER DEFAULT 0,
                    is_ready BOOLEAN DEFAULT FALSE,
                    join_order SERIAL,
                    PRIMARY KEY (room_code, user_id)
                );
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE,
                    image_url TEXT,
                    display_order INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS words (
                    id SERIAL PRIMARY KEY,
                    category TEXT REFERENCES categories(name) ON DELETE CASCADE,
                    word TEXT
                );
                -- تحديث جدول المستخدمين ليشمل إحصائيات
                ALTER TABLE users ADD COLUMN IF NOT EXISTS total_wins INTEGER DEFAULT 0;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS saved_players JSONB DEFAULT '[]';
                ALTER TABLE room_players ADD COLUMN IF NOT EXISTS join_order SERIAL;
                ALTER TABLE categories ADD COLUMN IF NOT EXISTS display_order INTEGER DEFAULT 0;
            """)
            conn.commit()
    finally: conn.close()

init_db()

# --- Game Data ---
CATEGORIES = {
    "أكلات": ["بيتزا", "برجر", "شاورما", "منسف", "كبسة", "فلافل", "مندي", "باستا", "دولمة", "برياني", "مسحب", "كبة", "بخاري", "مقلوبة", "سوشي", "تاكو", "ملوخية", "باشميل"],
    "حيوانات": ["أسد", "نمر", "زرافة", "فيل", "قطة", "كلب", "أرنب", "قرد", "تمساح", "ثعلب", "ذئب", "جمل", "حصان", "سنجاب", "بطريق", "دولفين", "قرش"],
    "ملابس": ["قميص", "بنطلون", "فستان", "تنورة", "جاكيت", "قبعة", "جوارب", "حذاء", "ربطة عنق", "بلوزة", "بشت", "شماغ", "عباية", "هودي"],
    "كورة": ["ريال مدريد", "برشلونة", "ليفربول", "الهلال", "النصر", "الاتحاد", "الاهلي", "ميسي", "رونالدو", "صلاح", "مبابي", "نيمار", "مانشستر سيتي", "بايرن ميونخ"],
    "سيارات": ["تويوتا", "مرسيدس", "فورد", "تسلا", "نيسان", "هوندا", "بي ام دبليو", "لكزس", "مازدا", "كيا", "باجيرو", "لاند كروزر", "شفروليه", "كامري", "بنتلي"],
    "شركات": ["جوجل", "ابل", "مايكروسوفت", "سامسونج", "امازون", "فيسبوك", "تسلا", "كوكاكولا", "بيبسي", "نايكي", "اديداس", "هواوي", "سوني"],
    "كواكب": ["المريخ", "المشتري", "زحل", "الأرض", "الزهرة", "عطارد", "نبتون", "أورانوس", "الشمس", "القمر", "بلوتو"],
    "أجهزة": ["آيفون", "بليستيشن", "لابتوب", "تلفزيون", "ساعة ذكية", "كاميرا", "ايباد", "اكس بوكس", "بي سي", "سماعات", "غسالة", "مكيف", "ثلاجة", "مايكرويف"],
    "تطبيقات": ["واتساب", "انستقرام", "تيك توك", "سناب شات", "تلغرام", "يوتيوب", "تويتر", "فيسبوك", "ديسكورد", "سبوتيفاي", "نتفلكس", "بوجي"],
    "فواكه وخضار": ["تفاح", "موز", "مانجو", "فراولة", "بطيخ", "عنب", "برتقال", "أناناس", "كيوي", "توت", "كرز", "رمان", "خيار", "طماطم", "جزر", "بطاطس", "بصل"],
    "شخصيات": ["سوبرمان", "باتمان", "سبايدرمان", "جوكر", "هالك", "ايرون مان", "ثور", "كابتن امريكا", "ثانوس", "بلاك بانثر"],
    "كارتون": ["توم وجيري", "ميكي ماوس", "سبونج بوب", "بن 10", "غامبول", "سبيستون", "سابق ولاحق", "كونان", "بوكيمون", "سندباد"],
    "مشروبات": ["شاي", "قهوة", "عصير", "حليب", "بيبسي", "كوكاكولا", "ميرندا", "سفن اب", "كود رد", "بايسن", "موخيتو", "كركديه"],
    "حلويات": ["كنافة", "بسبوسة", "بقلاوة", "دونات", "تشيز كيك", "كيك", "كريب", "وافل", "ايس كريم", "ماكرون", "سينابون"],
    "مسلسلات": ["صراع العروش", "لا كاسا دي بابل", "بريكنج باد", "فريندز", "الموتى السائرون", "بيكي بلايندرز", "سكيد جيم", "رشاش"],
    "انمي": ["ون بيس", "ناروتو", "هجوم العمالقة", "دراجون بول", "هنتر", "بليتش", "كونان", "ديمون سلاير", "جوجوتسو", "ديث نوت"],
    "كيبوب": ["بي تي اس", "بلاك بينك", "اكسو", "توايس", "ستراي كيدز", "ريد فيلفيت", "ايتيز", "نيوجينز"],
    "قيمرز": ["نينجا", "بندريتا", "ابو فلة", "تي ام فيصل", "باور", "سيد", "اوشي", "شراود", "ميث"],
    "مهن": ["طيار", "دكتور", "مهندس", "طباخ", "شرطي", "رائد فضاء", "معلم", "لاعب كرة", "مبرمج", "حلاق"]
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
            cur.execute("SELECT user_id, username_key, player_name, password_key, saved_players FROM users WHERE username_key = %s AND password_key = %s",
                        (data['username'], data['password']))
            user = cur.fetchone()
            if user and not user.get('saved_players'): user['saved_players'] = []
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

    conn = get_db_conn()
    words = []
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT word FROM words WHERE category = %s", (category,))
                words = [r[0] for r in cur.fetchall()]
        finally: conn.close()

    if not words:
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

# --- Online Mode API ---

@app.post("/api/online/create")
async def create_room(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "DB Error"}
    try:
        room_code = ''.join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=5))
        with conn.cursor() as cur:
            cur.execute("INSERT INTO rooms (room_code, host_id, status) VALUES (%s, %s, 'waiting')",
                        (room_code, data['user_id']))
            cur.execute("INSERT INTO room_players (room_code, user_id, player_name) VALUES (%s, %s, %s)",
                        (room_code, data['user_id'], data['player_name']))
            conn.commit()
        return {"success": True, "room_code": room_code}
    finally: conn.close()

@app.post("/api/online/join")
async def join_room(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "DB Error"}
    try:
        room_code = data['room_code'].upper()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM rooms WHERE room_code = %s", (room_code,))
            if not cur.fetchone(): return {"success": False, "msg": "الغرفة غير موجودة"}
            cur.execute("INSERT INTO room_players (room_code, user_id, player_name) VALUES (%s, %s, %s) ON CONFLICT (room_code, user_id) DO UPDATE SET player_name = EXCLUDED.player_name",
                        (room_code, data['user_id'], data['player_name']))
            conn.commit()
        return {"success": True}
    finally: conn.close()

@app.post("/api/online/start")
async def start_online_game(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        room_code = data['room_code'].upper()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room or room['host_id'] != data['user_id']: return {"success": False}

            cur.execute("SELECT player_name FROM room_players WHERE room_code = %s ORDER BY join_order ASC", (room_code,))
            players = [p['player_name'] for p in cur.fetchall()]
            if len(players) < 3: return {"success": False, "msg": "أقل عدد لاعبين هو 3"}

            category = room['category'] or "أكلات"

            # محاولة جلب الكلمات من قاعدة البيانات أولاً
            words = []
            cur.execute("SELECT word FROM words WHERE category = %s", (category,))
            words = [r['word'] for r in cur.fetchall()]

            if not words:
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

            game_data = {
                "word": correct, "roles": roles, "guesses": guesses,
                "q_seq": q_seq, "spy_idx": spy_idx, "players": players,
                "current_phase": "roles", "q_idx": 0
            }

            cur.execute("UPDATE rooms SET status = 'playing', game_data = %s WHERE room_code = %s",
                        (json.dumps(game_data), room_code))
            # ريست لحالة الجاهزية للاعبين لبدء الجولة
            cur.execute("UPDATE room_players SET is_ready = FALSE WHERE room_code = %s", (room_code,))
            conn.commit()
        return {"success": True}
    finally: conn.close()

@app.get("/api/online/room/{room_code}")
async def get_room(room_code: str):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        room_code = room_code.upper()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room: return {"success": False}
            cur.execute("SELECT user_id, player_name, is_ready, score FROM room_players WHERE room_code = %s ORDER BY join_order ASC", (room_code,))
            players = cur.fetchall()
            return {"success": True, "room": room, "players": players}
    finally: conn.close()

@app.post("/api/online/action")
async def online_action(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        room_code = data['room_code'].upper()
        user_id = data['user_id']
        action = data['action']

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room: return {"success": False}

            game_data = room['game_data']

            if action == "ready_role":
                # تسجيل أن اللاعب قرأ دوره
                cur.execute("UPDATE room_players SET is_ready = TRUE WHERE room_code = %s AND user_id = %s", (room_code, user_id))
                # إذا الكل جاهز، ننتقل للمرحلة التالية
                cur.execute("SELECT COUNT(*) FROM room_players WHERE room_code = %s AND is_ready = FALSE", (room_code,))
                if cur.fetchone()['count'] == 0:
                    game_data['current_phase'] = 'questions'
                    game_data['q_idx'] = 0
                    cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                conn.commit()

            elif action == "next_question":
                if room['host_id'] == user_id:
                    game_data['q_idx'] = game_data.get('q_idx', 0) + 1
                    if game_data['q_idx'] >= len(game_data['q_seq']):
                        game_data['current_phase'] = 'voting'
                        # ريست لـ is_ready لاستخدامها في التصويت
                        cur.execute("UPDATE room_players SET is_ready = FALSE WHERE room_code = %s", (room_code,))
                    cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                    conn.commit()

            elif action == "vote":
                target = data['target']
                if 'votes' not in game_data: game_data['votes'] = {}
                # الحصول على اسم اللاعب المصوّت
                cur.execute("SELECT player_name FROM room_players WHERE room_code = %s AND user_id = %s", (room_code, user_id))
                voter_name = cur.fetchone()['player_name']
                game_data['votes'][voter_name] = target

                cur.execute("UPDATE room_players SET is_ready = TRUE WHERE room_code = %s AND user_id = %s", (room_code, user_id))

                # إذا الكل صوت
                cur.execute("SELECT COUNT(*) FROM room_players WHERE room_code = %s AND is_ready = FALSE", (room_code,))
                if cur.fetchone()['count'] == 0:
                    game_data['current_phase'] = 'reveal'

                cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                conn.commit()

            elif action == "spy_guess":
                guess = data['guess']
                game_data['spy_guess'] = guess
                game_data['current_phase'] = 'result'

                # توزيع النقاط (نفس منطق الـ offline)
                spy_name = game_data['players'][game_data['spy_idx']]
                spy_guessed_right = (guess == game_data['word'])

                # حساب الأصوات لمعرفة هل انكشف الجاسوس
                vote_counts = {}
                for p in game_data['players']: vote_counts[p] = 0
                for v in game_data['votes'].values(): vote_counts[v] = vote_counts.get(v, 0) + 1

                max_votes = 0
                voted_out = ""
                for p, count in vote_counts.items():
                    if count > max_votes:
                        max_votes = count
                        voted_out = p

                spy_caught = (voted_out == spy_name)

                # تحديث النقاط في قاعدة البيانات
                for voter_name, target in game_data['votes'].items():
                    if voter_name != spy_name and target == spy_name:
                        cur.execute("UPDATE room_players SET score = score + 1 WHERE room_code = %s AND player_name = %s", (room_code, voter_name))

                if spy_guessed_right:
                    cur.execute("UPDATE room_players SET score = score + 1 WHERE room_code = %s AND player_name = %s", (room_code, spy_name))

                cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                conn.commit()

            elif action == "new_round":
                if room['host_id'] == user_id:
                    cur.execute("SELECT player_name FROM room_players WHERE room_code = %s ORDER BY join_order ASC", (room_code,))
                    players = [p['player_name'] for p in cur.fetchall()]
                    category = room['category'] or "أكلات"

                    cur.execute("SELECT word FROM words WHERE category = %s", (category,))
                    words = [r['word'] for r in cur.fetchall()]
                    if not words: words = CATEGORIES.get(category, CATEGORIES["أكلات"])

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

                    game_data = {
                        "word": correct, "roles": roles, "guesses": guesses,
                        "q_seq": q_seq, "spy_idx": spy_idx, "players": players,
                        "current_phase": "roles", "q_idx": 0
                    }
                    cur.execute("UPDATE rooms SET status = 'playing', game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                    cur.execute("UPDATE room_players SET is_ready = FALSE WHERE room_code = %s", (room_code,))
                    conn.commit()

        return {"success": True}
    finally: conn.close()

@app.post("/api/admin/add_word")
async def add_word(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO words (category, word) VALUES (%s, %s)", (data['category'], data['word']))
            conn.commit()
        return {"success": True}
    finally: conn.close()

@app.get("/api/admin/words")
async def get_words():
    conn = get_db_conn()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM words ORDER BY category, word")
            return cur.fetchall()
    finally: conn.close()

# --- Admin Dashboard APIs ---

@app.get("/api/admin/players")
async def admin_get_players():
    conn = get_db_conn()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT user_id, username_key, player_name, total_wins FROM users ORDER BY total_wins DESC")
            return cur.fetchall()
    finally: conn.close()

@app.get("/api/categories")
async def get_categories():
    conn = get_db_conn()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM categories ORDER BY display_order ASC, name ASC")
            cats = cur.fetchall()
            # إذا الجدول فارغ، نعبئه بالبيانات الافتراضية
            if not cats:
                default_cats = ["أكلات", "حيوانات", "ملابس", "كورة", "سيارات", "شركات", "كواكب", "أجهزة", "تطبيقات", "فواكه وخضار", "شخصيات", "كارتون", "مشروبات", "حلويات", "مسلسلات", "انمي", "كيبوب", "قيمرز", "مهن"]
                for i, c in enumerate(default_cats):
                    cur.execute("INSERT INTO categories (name, display_order) VALUES (%s, %s) ON CONFLICT DO NOTHING", (c, i))
                conn.commit()
                cur.execute("SELECT * FROM categories ORDER BY display_order ASC, name ASC")
                cats = cur.fetchall()
            return cats
    finally: conn.close()

@app.post("/api/admin/category/add")
async def add_category(data: dict):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO categories (name, image_url, display_order) VALUES (%s, %s, %s)",
                        (data['name'], data.get('image_url'), data.get('display_order', 0)))
            conn.commit()
        return {"success": True}
    finally: conn.close()

@app.post("/api/admin/category/update")
async def update_category(data: dict):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            # تحديث اسم الفئة في جدول الكلمات أولاً إذا تغير الاسم
            if 'old_name' in data and data['old_name'] != data['name']:
                cur.execute("UPDATE words SET category = %s WHERE category = %s", (data['name'], data['old_name']))

            cur.execute("UPDATE categories SET name = %s, image_url = %s, display_order = %s WHERE id = %s",
                        (data['name'], data.get('image_url'), data.get('display_order', 0), data['id']))
            conn.commit()
        return {"success": True}
    finally: conn.close()

@app.post("/api/admin/category/delete")
async def delete_category(data: dict):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM categories WHERE id = %s", (data['id'],))
            conn.commit()
        return {"success": True}
    finally: conn.close()

@app.post("/api/admin/word/delete")
async def delete_word(data: dict):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM words WHERE id = %s", (data['id'],))
            conn.commit()
        return {"success": True}
    finally: conn.close()

@app.post("/api/user/save_players")
async def save_players(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET saved_players = %s WHERE user_id = %s",
                        (json.dumps(data['players']), data['user_id']))
            conn.commit()
        return {"success": True}
    finally: conn.close()

@app.post("/api/game/report_winner")
async def report_winner(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        with conn.cursor() as cur:
            # تحديث اللاعب في جدول المستخدمين الرئيسي (إذا كان مسجلاً)
            cur.execute("UPDATE users SET total_wins = total_wins + 1 WHERE player_name = %s", (data['player_name'],))

            # تحديث قائمة اللاعبين المحليين للمستخدم الحالي (Host)
            if 'user_id' in data:
                cur.execute("SELECT saved_players FROM users WHERE user_id = %s", (data['user_id'],))
                row = cur.fetchone()
                if row:
                    players = row[0] if row[0] is not None else []
                    updated = False
                    for i, p in enumerate(players):
                        p_name = p if isinstance(p, str) else p.get('name')
                        if p_name == data['player_name']:
                            if isinstance(p, str):
                                players[i] = {"name": p, "wins": 1}
                            else:
                                p['wins'] = p.get('wins', 0) + 1
                            updated = True
                            break
                    if updated:
                        cur.execute("UPDATE users SET saved_players = %s WHERE user_id = %s", (json.dumps(players), data['user_id']))
            conn.commit()
        return {"success": True}
    finally: conn.close()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>برا السالفة | المجلس</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#6c5ce7">
    <link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/8030/8030198.png">
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #6c5ce7; --bg: #0f0c29; --card: #1b1464; --accent: #f9ca24; --error: #eb4d4b; --success: #2ecc71; }
        body { font-family: 'Cairo', sans-serif; background: var(--bg); color: white; margin: 0; min-height: 100vh; }
        .flex-center { display: flex; justify-content: center; align-items: center; min-height: 100vh; flex-direction: column; }
        .container { width: 95%; max-width: 500px; text-align: center; padding: 20px; box-sizing: border-box; }
        .card { background: var(--card); padding: 30px; border-radius: 30px; box-shadow: 0 15px 35px rgba(0,0,0,0.6); border: 2px solid #3c339e; animation: fadeIn 0.3s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideIn { from { transform: translateX(100px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .reveal-text { animation: pop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
        @keyframes pop { 0% { transform: scale(0.5); } 100% { transform: scale(1); } }
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
        .score-item { display: flex; justify-content: space-between; background: #0f0c29; padding: 10px 20px; border-radius: 10px; margin: 5px 0; border: 1px solid #3c339e; }
        .cat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 20px 0; max-height: 300px; overflow-y: auto; padding: 10px; }
        .cat-card { background: #130f40; border-radius: 15px; padding: 10px; cursor: pointer; border: 2px solid transparent; transition: 0.3s; display: flex; flex-direction: column; align-items: center; }
        .cat-card img { width: 100%; height: 60px; object-fit: cover; border-radius: 10px; margin-bottom: 5px; }
        .cat-card.selected { border-color: var(--accent); background: #1b1464; box-shadow: 0 0 15px var(--accent); }
        .win-opt {
            padding: 10px 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            cursor: pointer;
            transition: 0.3s;
            border: 2px solid transparent;
            font-weight: bold;
        }
        .win-opt.selected {
            background: var(--accent);
            color: white;
            border-color: white;
        }
        .cat-card span { font-size: 12px; font-weight: bold; }
        .no-img { width: 100%; height: 60px; background: #2f278c; display: flex; align-items: center; justify-content: center; border-radius: 10px; font-size: 24px; }
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
        <button style="background:var(--success); font-size:14px;" onclick="showReports()">📊 التقارير والمتصدرين</button>
        <button style="background:var(--primary); font-size:14px;" onclick="showEditProfile()">تعديل بيانات الحساب</button>
        <button style="background:var(--error); font-size:14px;" onclick="logout()">تسجيل الخروج</button>
        <button style="background:#636e72; font-size:14px;" onclick="toggleSidebar()">إغلاق</button>
    </div>
    <div class="flex-center"><div class="container" id="main-ui"></div></div>
    <script>
        let currentUser = JSON.parse(localStorage.getItem('user')) || null;
        let game = null;
        let p_votes = {};
        let totalScores = {}; // نقاط الجلسة
        let winLimit = 1000;

        function init() {
            const urlParams = new URLSearchParams(window.location.search);
            const joinCode = urlParams.get('join');
            if (joinCode) {
                window.history.replaceState({}, document.title, window.location.pathname);
                localStorage.setItem('pendingJoin', joinCode);
            }
            currentUser ? showMenu() : showAuth();
            updateSidebar();
            if (currentUser && localStorage.getItem('pendingJoin')) {
                const code = localStorage.getItem('pendingJoin');
                localStorage.removeItem('pendingJoin');
                joinRoomByCode(code);
            }
        }

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
            totalScores = {}; // ريست للنقاط عند العودة للقائمة
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h1>ابدأ اللعب</h1>
                    <button onclick="showOnlineMenu()">🌐 أونلاين</button>
                    <button style="background:#e056fd" onclick="showSetup(1)">🏠 أوفلاين (مجلس)</button>
                </div>`;
        }

        // --- Online Logic ---
        let currentRoom = null;
        let pollInterval = null;

        function showOnlineMenu() {
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h1>اللعب أونلاين</h1>
                    <button style="background:var(--success)" onclick="createRoom()">إنشاء غرفة جديدة</button>
                    <div style="margin:20px 0;">
                        <input id="join_code" placeholder="رمز الغرفة (مثال: ABCD)" style="text-transform:uppercase">
                        <button onclick="joinRoom()">دخول غرفة</button>
                    </div>
                    <button style="background:#636e72" onclick="showMenu()">رجوع</button>
                </div>`;
        }

        async function createRoom() {
            const res = await fetch('/api/online/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: currentUser.user_id, player_name: currentUser.player_name})
            });
            const d = await res.json();
            if(d.success) enterRoom(d.room_code);
        }

        async function joinRoom() {
            const code = document.getElementById('join_code').value.trim().toUpperCase();
            if(!code) return;
            const res = await fetch('/api/online/join', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({room_code: code, user_id: currentUser.user_id, player_name: currentUser.player_name})
            });
            const d = await res.json();
            if(d.success) enterRoom(code); else alert(d.msg);
        }

        function enterRoom(code) {
            currentRoom = code;
            startPolling();
            renderRoom();
        }

        function startPolling() {
            if(pollInterval) clearInterval(pollInterval);
            pollInterval = setInterval(updateRoomState, 2000);
        }

        async function updateRoomState() {
            if(!currentRoom) return;
            const res = await fetch(`/api/online/room/${currentRoom}`);
            const d = await res.json();
            if(d.success) {
                window.roomData = d;
                if(d.room.status === 'playing') {
                    game = d.room.game_data;
                    game.isOnline = true;
                    if(game.current_phase === 'roles') {
                        showOnlineRole();
                    } else if(game.current_phase === 'questions') {
                        showOnlineQuestions();
                    } else if(game.current_phase === 'voting') {
                        showOnlineVoting();
                    } else if(game.current_phase === 'reveal') {
                        showOnlineReveal();
                    } else if(game.current_phase === 'result') {
                        showOnlineResult();
                    }
                } else {
                    renderRoom();
                }
            }
        }

        function renderRoom() {
            if(!window.roomData) {
                document.getElementById('main-ui').innerHTML = `<div class="card">جاري التحميل...</div>`;
                return;
            }
            const {room, players} = window.roomData;
            let pList = players.map(p => `<div class="score-item"><span>${p.player_name}</span> ${p.is_ready ? '✅' : '⏳'}</div>`).join('');

            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>غرفة: <span style="color:var(--accent)">${room.room_code}</span></h2>
                    <button style="background:var(--primary); margin-bottom:10px; font-size:14px;" onclick="copyInviteLink()">🔗 نسخ رابط الدعوة</button>
                    <div style="margin:10px 0; text-align:right;">${pList}</div>
                    ${room.host_id == currentUser.user_id ? `
                        <select id="online_cat" style="margin-bottom:10px">${["أكلات", "حيوانات", "ملابس", "كورة", "سيارات", "شركات", "كواكب", "أجهزة", "تطبيقات", "فواكه وخضار", "شخصيات", "كارتون", "مشروبات", "حلويات", "مسلسلات", "انمي", "كيبوب", "قيمرز", "مهن"].map(c=>`<option value="${c}">${c}</option>`)}</select>
                        <button onclick="startOnlineGame()">بدء اللعبة</button>` :
                        '<p>بانتظار المضيف لبدء اللعبة...</p>'}
                    <button style="background:#636e72" onclick="leaveRoom()">خروج</button>
                </div>`;
        }

        function copyInviteLink() {
            const url = window.location.origin + '?join=' + currentRoom;
            navigator.clipboard.writeText(url).then(() => {
                alert("تم نسخ رابط الدعوة! أرسله لأصدقائك.");
            });
        }

        async function joinRoomByCode(code) {
            const res = await fetch('/api/online/join', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({room_code: code, user_id: currentUser.user_id, player_name: currentUser.player_name})
            });
            const d = await res.json();
            if(d.success) enterRoom(code); else alert(d.msg);
        }

        async function startOnlineGame() {
            const res = await fetch('/api/online/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({room_code: currentRoom, user_id: currentUser.user_id})
            });
            const d = await res.json();
            if(!d.success) alert(d.msg || "تعذر بدء اللعبة");
        }

        function showOnlineRole() {
            const myIdx = window.roomData.players.findIndex(p => p.user_id === currentUser.user_id);
            if(myIdx === -1) return;
            const me = window.roomData.players[myIdx];

            if(me.is_ready) {
                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h3>بانتظار بقية اللاعبين...</h3>
                        <div class="shuffling">⏳</div>
                    </div>`;
                return;
            }

            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h3>أنت: <b style="color:var(--accent)">${currentUser.player_name}</b></h3>
                    <div id="box" style="background:#0f0c29; padding:20px; border-radius:20px; margin:20px 0;">
                        <h3>${game.roles[myIdx] === 'spy' ? '🕵️ أنت برة السالفة!' : '🤫 السالفة هي: ' + game.word}</h3>
                    </div>
                    <button onclick="onlineAction('ready_role')">فهمت، جاهز</button>
                </div>`;
        }

        async function onlineAction(action, extra = {}) {
            await fetch('/api/online/action', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({room_code: currentRoom, user_id: currentUser.user_id, action, ...extra})
            });
        }

        function showOnlineQuestions() {
            const q = game.q_seq[game.q_idx];
            const isHost = window.roomData.room.host_id == currentUser.user_id;

            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <span class="q-badge">مرحلة الأسئلة</span>
                    <div style="font-size:24px; margin:30px 0;">
                        <b style="color:#a29bfe">${q.f}</b> يسأل <b style="color:#ff7675">${q.t}</b>
                    </div>
                    ${isHost ? `<button onclick="onlineAction('next_question')">السؤال التالي</button>` : `<p>بانتظار المضيف...</p>`}
                </div>`;
        }

        function showOnlineVoting() {
            const myIdx = window.roomData.players.findIndex(p => p.user_id === currentUser.user_id);
            const me = window.roomData.players[myIdx];

            if(me.is_ready) {
                document.getElementById('main-ui').innerHTML = `<div class="card"><h3>تم إرسال صوتك...</h3><div class="shuffling">⏳</div></div>`;
                return;
            }

            let h = `<h3>صوت سراً: منو اللي برة السالفة؟</h3><div id="vbox"></div>`;
            document.getElementById('main-ui').innerHTML = `<div class="card">${h}</div>`;

            game.players.forEach(p => {
                let btn = document.createElement('button'); btn.className = 'vote-item'; btn.innerText = p;
                btn.onclick = () => onlineAction('vote', {target: p});
                document.getElementById('vbox').appendChild(btn);
            });
        }

        function showOnlineReveal() {
            const spy = game.players[game.spy_idx];
            const isSpy = game.roles[window.roomData.players.findIndex(p => p.user_id === currentUser.user_id)] === 'spy';

            if(isSpy) {
                let h = `<h3>كشفوك! خمن وش السالفة؟</h3>`;
                game.guesses.forEach(g => h += `<div class="vote-item" onclick="onlineAction('spy_guess', {guess: '${g}'})">${g}</div>`);
                document.getElementById('main-ui').innerHTML = `<div class="card">${h}</div>`;
            } else {
                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h1>اللي برة السالفة هو:</h1>
                        <h2 style="color:var(--error); font-size:40px;">${spy}</h2>
                        <p>بانتظار تخمين الجاسوس...</p>
                        <div class="shuffling">🌀</div>
                    </div>`;
            }
        }

        function showOnlineResult() {
            const spy = game.players[game.spy_idx];
            const spyGuessedRight = (game.spy_guess === game.word);
            const isHost = window.roomData.room.host_id == currentUser.user_id;

            let scoresList = "";
            window.roomData.players.sort((a,b) => b.score - a.score).forEach(p => {
                scoresList += `<div class="score-item"><span>${p.player_name}</span> <b>${p.score}</b></div>`;
            });

            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2 style="color:${spyGuessedRight? 'var(--success)':'var(--error)'}">السالفة كانت: ${game.word}</h2>
                    <p>${spy} ${spyGuessedRight ? 'عرف السالفة!' : 'ما عرف السالفة.'}</p>
                    <hr style="border:1px solid #3c339e; margin:15px 0;">
                    <h3>النقاط الحالية:</h3>
                    <div style="margin-bottom:20px;">${scoresList}</div>
                    ${isHost ? `<button onclick="startOnlineGame()">جولة جديدة</button>` : `<p>بانتظار المضيف لبدء جولة جديدة...</p>`}
                    <button style="background:#636e72" onclick="leaveRoom()">خروج من الغرفة</button>
                </div>`;
        }

        function leaveRoom() {
            clearInterval(pollInterval);
            currentRoom = null;
            showMenu();
        }

        function showEditProfile() {
            toggleSidebar();
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>تعديل بياناتي</h2>
                    <input id="edit_u" value="${currentUser.username_key}">
                    <input id="edit_n" value="${currentUser.player_name}">
                    <input id="edit_p" type="password" value="${currentUser.password_key}">
                    <button onclick="updateProfile()">حفظ التعديلات</button>
                    <button style="background:#636e72" onclick="showMenu()">إلغاء</button>
                </div>`;
        }

        async function updateProfile() {
            const res = await fetch('/api/auth/update', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({old_username: currentUser.username_key, username: edit_u.value, password: edit_p.value, name: edit_n.value})});
            const d = await res.json();
            if(d.success) { alert("تم التحديث! سجل دخولك مجدداً"); logout(); } else alert(d.msg);
        }

        function changePCount(delta) {
            let val = parseInt(localStorage.getItem('pCount') || 3) + delta;
            if(val >= 3 && val <= 20) {
                localStorage.setItem('pCount', val);

                let inp = document.getElementById('p_count');
                if(inp) inp.value = val;

                const reqEl = document.getElementById('required_n_display');
                if(reqEl) reqEl.innerText = val;

                updateSelectedCount();
            }
        }
        function saveAndNext() {
            localStorage.setItem('pCount', document.getElementById('p_count').value);
            showSetup(2);
        }

        function togglePSelection(el, name) {
            const icon = el.querySelector('.status-icon');
            if(icon.innerText === '✅') {
                icon.innerText = '⬜';
            } else {
                const targetN = parseInt(localStorage.getItem('pCount') || 3);
                const currentCount = Array.from(document.querySelectorAll('.status-icon')).filter(i => i.innerText === '✅').length;
                if(currentCount >= targetN) {
                    alert("لقد اخترت العدد المطلوب فعلاً (" + targetN + ") لاعبين");
                    return;
                }
                icon.innerText = '✅';
            }
            updateSelectedCount();
        }

        function updateSelectedCount() {
            const count = Array.from(document.querySelectorAll('.status-icon')).filter(i => i.innerText === '✅').length;
            const counterEl = document.getElementById('selected_count');
            if(counterEl) counterEl.innerText = count;

            const nextBtn = document.querySelector('button[onclick="confirmPlayersAndNext()"]');
            if(nextBtn) {
                const targetN = parseInt(localStorage.getItem('pCount') || 3);
                nextBtn.disabled = (count !== targetN);
                nextBtn.style.opacity = (count === targetN) ? "1" : "0.5";
            }
        }

        async function addNewPlayerToList() {
            const nameInp = document.getElementById('new_p_name');
            const name = nameInp.value.trim();
            if(!name) return;

            if(!currentUser.saved_players) currentUser.saved_players = [];

            // البحث عن اللاعب إذا كان موجوداً مسبقاً
            const existingIdx = currentUser.saved_players.findIndex(p => {
                const pName = (typeof p === 'string' ? p : p.name).trim();
                return pName.toLowerCase() === name.toLowerCase();
            });

            if(existingIdx !== -1) {
                const items = document.querySelectorAll('#p_selection_list .score-item');
                for(let item of items) {
                    const spanName = item.querySelector('span').innerText.trim();
                    if(spanName.toLowerCase() === name.toLowerCase()) {
                        item.scrollIntoView({behavior: 'smooth', block: 'center'});
                        item.style.transition = "all 0.3s";
                        item.style.background = "rgba(162, 155, 254, 0.5)";
                        item.style.transform = "scale(1.05)";

                        const icon = item.querySelector('.status-icon');
                        if(icon.innerText === '⬜') {
                            togglePSelection(item, spanName);
                        }

                        setTimeout(() => {
                            item.style.background = "";
                            item.style.transform = "";
                        }, 2000);

                        nameInp.value = "";
                        return;
                    }
                }
            }

            // إضافة لاعب جديد
            currentUser.saved_players.push({name: name, wins: 0});
            localStorage.setItem('user', JSON.stringify(currentUser));
            showSetup(2); // تحديث الواجهة فوراً

            // حفظ في الخلفية
            fetch('/api/user/save_players', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: currentUser.user_id, players: currentUser.saved_players})
            });
        }

        function confirmPlayersAndNext() {
            const targetN = parseInt(localStorage.getItem('pCount'));
            const selected = Array.from(document.querySelectorAll('#p_selection_list .score-item'))
                .filter(el => el.querySelector('.status-icon').innerText === '✅')
                .map(el => el.querySelector('span').innerText);

            if(selected.length !== targetN) {
                if(confirm(`لقد اخترت ${selected.length} لاعبين، والمطلوب ${targetN}. هل تريد تغيير عدد اللاعبين إلى ${selected.length} والبدء؟`)) {
                    localStorage.setItem('pCount', selected.length);
                } else {
                    return;
                }
            }
            window.pNamesSave = selected;
            showSetup(3);
        }

        async function showSetup(step) {
            if(step === 1) {
                let savedCount = localStorage.getItem('pCount') || 3;
                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2>عدد اللاعبين</h2>
                        <div style="display: flex; align-items: center; justify-content: center; gap: 15px; margin: 20px 0;">
                            <button onclick="changePCount(-1)" style="width: 60px; margin:0; background:var(--error); font-size: 24px;">-</button>
                            <input type="number" id="p_count" value="${savedCount}" min="3" style="text-align: center; width: 100px; margin:0; font-size: 24px; font-weight: bold;">
                            <button onclick="changePCount(1)" style="width: 60px; margin:0; background:var(--success); font-size: 24px;">+</button>
                        </div>
                        <button onclick="saveAndNext()">التالي</button>
                        <button style="background:#636e72" onclick="showMenu()">رجوع</button>
                    </div>`;
            } else if(step === 2) {
                const targetN = Math.max(3, parseInt(localStorage.getItem('pCount') || 3));
                let savedPlayers = currentUser.saved_players || [];

                let h = `<div id="p_selection_list" style="max-height: 300px; overflow-y: auto; margin-bottom: 20px; text-align: right;">`;

                // عرض اللاعبين المخزنين أولاً مع خاصية الاختيار
                savedPlayers.forEach((p, idx) => {
                    const name = typeof p === 'string' ? p : p.name;
                    const isSelected = idx < targetN;
                    h += `
                        <div class="score-item" style="cursor:pointer" onclick="togglePSelection(this, '${name.replace(/'/g, "\\'")}')">
                            <span>${name}</span>
                            <span class="status-icon">${isSelected ? '✅' : '⬜'}</span>
                        </div>`;
                });
                h += `</div>`;

                // حقل لإضافة لاعب جديد للقائمة
                h += `
                    <div style="display:flex; gap:10px;">
                        <input id="new_p_name" placeholder="اسم لاعب جديد" style="margin:0">
                        <button onclick="addNewPlayerToList()" style="width:80px; margin:0; background:var(--success)">+</button>
                    </div>

                    <div style="display: flex; align-items: center; justify-content: center; gap: 10px; margin-top: 15px; background: rgba(255,255,255,0.05); padding: 5px; border-radius: 10px;">
                        <button onclick="changePCount(-1)" style="width: 40px; height: 35px; margin:0; background:var(--error); display: flex; align-items: center; justify-content: center; font-size: 20px;">-</button>
                        <span style="font-weight:bold; font-size:14px;">تعديل العدد المطلوب</span>
                        <button onclick="changePCount(1)" style="width: 40px; height: 35px; margin:0; background:var(--success); display: flex; align-items: center; justify-content: center; font-size: 20px;">+</button>
                    </div>

                    <p id="selection_info" style="margin-top:10px; font-size:14px; color:var(--accent)">
                        المطلوب: <span id="required_n_display">${targetN}</span> لاعبين | المختار: <span id="selected_count">0</span>
                    </p>
                    <button onclick="confirmPlayersAndNext()">التالي</button>`;

                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2>اختر اللاعبين</h2>
                        ${h}
                    </div>`;

                // تحديث العداد الأولي
                updateSelectedCount();
            } else if(step === 3) {
                const res = await fetch('/api/categories');
                const cats = await res.json();

                let catsHtml = "";
                cats.forEach(c => {
                    catsHtml += `
                        <div class="cat-card" onclick="selectCat(this, '${c.name}')">
                            ${c.image_url ? `<img src="${c.image_url}">` : '<div class="no-img">؟</div>'}
                            <span>${c.name}</span>
                        </div>`;
                });

                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2>اختر نوع السالفة</h2>
                        <div class="cat-grid">${catsHtml}</div>
                        <input type="hidden" id="selected_cat">

                        <p style="margin-top:20px; font-weight:bold;">حد الفوز (نقاط):</p>
                        <div style="display: flex; gap: 10px; justify-content: center; margin-bottom: 20px;">
                            <div class="win-opt" onclick="selectWinLimit(this, 5)">5</div>
                            <div class="win-opt selected" onclick="selectWinLimit(this, 10)">10</div>
                            <div class="win-opt" onclick="selectWinLimit(this, 15)">15</div>
                            <div class="win-opt" onclick="selectWinLimit(this, 20)">20</div>
                        </div>
                        <input type="hidden" id="win_limit_val" value="10">

                        <button onclick="startGameFinal()">ابدأ اللعب الآن</button>
                    </div>`;
            }
        }

        function selectWinLimit(el, val) {
            document.querySelectorAll('.win-opt').forEach(opt => opt.classList.remove('selected'));
            el.classList.add('selected');
            document.getElementById('win_limit_val').value = val;
        }

        function selectCat(el, name) {
            document.querySelectorAll('.cat-card').forEach(c => c.classList.remove('selected'));
            el.classList.add('selected');
            document.getElementById('selected_cat').value = name;
        }

        function startGameFinal() {
            const cat = document.getElementById('selected_cat').value;
            if(!cat) return alert("اختر فئة أولاً!");
            winLimit = parseInt(document.getElementById('win_limit_val').value);
            start(cat);
        }

        async function start(category) {
            const players = window.pNamesSave;
            if(Object.keys(totalScores).length === 0) players.forEach(p => totalScores[p] = 0);
            const res = await fetch('/api/game/start', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({players, category})});
            game = await res.json();
            game.players = players;
            game.category = category; // حفظ الفئة للجولة القادمة
            game.curr = 0;
            game.qIdx = 0;
            showRole();
        }

        function showRole() {
            if(game.curr >= game.players.length) { showPhase1(); return; }
            // صوت الكشف
            if(game.curr > 0) playSound('reveal');
            document.getElementById('main-ui').innerHTML = `
                <div class="card" style="animation: slideIn 0.4s ease-out">
                    <p>مرر الجهاز لـ</p><h2 style="color:var(--accent)">${game.players[game.curr]}</h2>
                    <div id="box" class="hidden" style="background:#0f0c29; padding:20px; border-radius:20px; margin:20px 0;">
                        <h3 class="reveal-text">${game.roles[game.curr] === 'spy' ? '🕵️ أنت برة السالفة!' : '🤫 السالفة هي: ' + game.word}</h3>
                    </div>
                    <button onclick="document.getElementById('box').classList.remove('hidden'); this.style.display='none'; document.getElementById('bnxt').style.display='block'; playSound('click')">اكشف الدور</button>
                    <button id="bnxt" style="display:none" onclick="game.curr++; showRole()">فهمت، التالي</button>
                </div>`;
        }

        function showPhase1() {
            if(game.qIdx >= game.q_seq.length) { showPhase2(game.players[0]); return; }
            const q = game.q_seq[game.qIdx];
            document.getElementById('main-ui').innerHTML = `
                <div class="card"><span class="q-badge">مرحلة إجبارية</span>
                    <div style="font-size:24px; margin:30px 0;"><b style="color:#a29bfe">${q.f}</b> يسأل <b style="color:#ff7675">${q.t}</b></div>
                    <button onclick="game.qIdx++; showPhase1()">السؤال التالي</button>
                    <button style="background: #ffec00; color: #1b1464; font-weight: 900; box-shadow: 0 0 20px rgba(255, 236, 0, 0.4);" onclick="startVoting()">إنهاء الجولة والتصويت</button>
                </div>`;
        }

        function showPhase2(asker, last = "") {
            document.getElementById('main-ui').innerHTML = `
                <div class="card"><span class="q-badge" style="background:var(--primary)">مرحلة الاختيار الحر</span>
                    <h3>دور <b style="color:var(--accent)">${asker}</b> يختار مين يسأل؟</h3>
                    <div id="plist"></div>
                    <button style="margin-top:20px; background: #ffec00; color: #1b1464; font-weight: 900; box-shadow: 0 0 20px rgba(255, 236, 0, 0.4);" onclick="startVoting()">بدء التصويت</button>
                </div>`;
            game.players.forEach(p => { if(p!==asker && p!==last) document.getElementById('plist').innerHTML += `<button class="vote-item" onclick="showPhase2('${p}', '${asker}')">اسأل ${p}</button>`; });
        }

        function startVoting() { p_votes = {}; performVote(0); }

        function performVote(idx) {
            if(idx >= game.players.length) { showReveal(); return; }
            let list = [...game.players].sort(() => Math.random() - 0.5);
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <p>مرر لـ <b>${game.players[idx]}</b></p>
                    <p>صوت سراً: منو اللي برة السالفة؟</p>
                    <div id="vbox"></div>
                </div>`;
            list.forEach(p => {
                let btn = document.createElement('button'); btn.className = 'vote-item'; btn.innerText = p;
                btn.onclick = () => { p_votes[game.players[idx]] = p; performVote(idx+1); };
                document.getElementById('vbox').appendChild(btn);
            });
        }

        function showReveal() {
            document.getElementById('main-ui').innerHTML = `<div class="card"><h1>جاري فرز الأصوات...</h1><div class="shuffling">🌀</div></div>`;
            setTimeout(() => {
                const spy = game.players[game.spy_idx];
                let resultsHtml = "";
                let voteCounts = {};
                game.players.forEach(p => voteCounts[p] = 0);

                Object.keys(p_votes).forEach(voter => {
                    const target = p_votes[voter];
                    voteCounts[target]++;
                    const isCorrect = (target === spy);
                    resultsHtml += `<div style="margin:5px 0;">${voter} صوّت لـ ${target} ${isCorrect?'✅':'❌'}</div>`;
                });

                // هل انكشف الجاسوس؟ (الأغلبية صوتت عليه)
                let maxVotes = 0, votedOut = "";
                for(let p in voteCounts) { if(voteCounts[p] > maxVotes) { maxVotes = voteCounts[p]; votedOut = p; } }
                game.spyCaught = (votedOut === spy);

                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h1>اللي برة السالفة هو:</h1>
                        <h2 style="color:var(--error); font-size:40px;">${spy}</h2>
                        <div style="background:#0f0c29; padding:15px; border-radius:15px; margin:20px 0; text-align:right;">${resultsHtml}</div>
                        <h3>${game.spyCaught ? '🚨 تم كشف الجاسوس!' : '🏃 هرب الجاسوس!'}</h3>
                        <button onclick="spyGuess()">التالي</button>
                    </div>`;
            }, 2000);
        }

        function spyGuess() {
            let h = `<h3>خمن وش السالفة؟ (فرصتك الأخيرة كجاسوس)</h3>`;
            game.guesses.forEach(g => h += `<div class="vote-item" onclick="finish('${g}')">${g}</div>`);
            document.getElementById('main-ui').innerHTML = `<div class="card">${h}</div>`;
        }

        function finish(guessedWord) {
            const spy = game.players[game.spy_idx];
            const spyGuessedRight = (guessedWord === game.word);
            let roundMsg = "";

            // توزيع النقاط حسب القواعد الصحيحة:
            // 1. اللاعبين (غير الجاسوس) اللي صوّتوا صح على الجاسوس ياخذون نقطة
            game.players.forEach(p => {
                if(p !== spy && p_votes[p] === spy) {
                    totalScores[p] = (totalScores[p] || 0) + 1;
                }
            });

            // 2. الجاسوس ياخذ نقطة فقط إذا عرف الكلمة (الشغلة)
            if (spyGuessedRight) {
                totalScores[spy] = (totalScores[spy] || 0) + 1;
                roundMsg = "الجاسوس عرف السالفة وأخذ نقطة!";
            } else {
                roundMsg = "الجاسوس ما عرف السالفة.";
            }

            if (game.spyCaught) {
                roundMsg += " وتم كشفه من اللاعبين (نقاط لمن صوّت صح)!";
            } else {
                roundMsg += " وهرب من التصويت!";
            }

            // فحص الفائز النهائي
            let sortedScores = Object.entries(totalScores).sort((a,b) => b[1]-a[1]);
            let hasWinner = sortedScores.some(s => s[1] >= winLimit);

            if(hasWinner) {
                playSound('win');
                // ابلاغ السيرفر بالفائز لتحديث الاحصائيات المحلية
                const winnerName = sortedScores[0][0];
                fetch('/api/game/report_winner', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({player_name: winnerName, user_id: currentUser.user_id})
                });

                let podiumHtml = "";
                const medals = ["🥇 المركز الأول", "🥈 المركز الثاني", "🥉 المركز الثالث"];
                const colors = ["gold", "silver", "#cd7f32"];

                for(let i=0; i<3; i++) {
                    if(sortedScores[i]) {
                        podiumHtml += `<div style="color:${colors[i]}; font-size:${24-i*2}px; margin:10px 0; font-weight:bold;">
                            ${medals[i]}: ${sortedScores[i][0]} (${sortedScores[i][1]} نقطة)
                        </div>`;
                    }
                }

                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h1 style="color:var(--accent)">🏆 النتائج النهائية 🏆</h1>
                        <div style="margin: 30px 0; background: rgba(0,0,0,0.3); padding: 20px; border-radius: 20px;">
                            ${podiumHtml}
                        </div>
                        <button onclick="showMenu()">العودة للقائمة الرئيسية</button>
                    </div>`;
            } else {
                let scoresList = "";
                sortedScores.forEach(([p, s]) => {
                    scoresList += `<div class="score-item"><span>${p}</span> <b>${s}</b></div>`;
                });
                document.getElementById('main-ui').innerHTML = `
                    <div class="card">
                        <h2 style="color:${spyGuessedRight? 'var(--success)':'var(--error)'}">${spyGuessedRight?'صح!':'خطأ!'} السالفة كانت: ${game.word}</h2>
                        <p>${roundMsg}</p>
                        <hr style="border:1px solid #3c339e; margin:15px 0;">
                        <h3>لوحة الصدارة (الهدف: ${winLimit}):</h3>
                        <div style="margin-bottom:20px;">${scoresList}</div>
                        <button onclick="start(game.category)">بدء جولة جديدة</button>
                        <button style="background:#636e72" onclick="showMenu()">إنهاء الجلسة</button>
                    </div>`;
            }
        }

        function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }
        function updateSidebar() { if(currentUser) {
            document.getElementById('user-display').innerText = currentUser.player_name;
            if(currentUser.username_key === 'admin') {
                if(!document.getElementById('admin-btn')) {
                    let btn = document.createElement('button');
                    btn.id = 'admin-btn';
                    btn.innerText = "🛠️ لوحة الإدارة";
                    btn.style.background = "var(--accent)";
                    btn.style.color = "black";
                    btn.onclick = showAdminDashboard;
                    document.getElementById('sidebar').appendChild(btn);
                }
            }
        }}

        async function showAdminDashboard() {
            toggleSidebar();
            document.getElementById('main-ui').innerHTML = `
                <div class="card">
                    <h2>لوحة التحكم الإدارية</h2>
                    <button onclick="adminManagePlayers()">👥 إدارة اللاعبين</button>
                    <button onclick="adminManageCategories()">📂 إدارة الفئات والكلمات</button>
                    <button style="background:#636e72" onclick="showMenu()">رجوع</button>
                </div>`;
        }

        async function adminManagePlayers() {
            const res = await fetch('/api/admin/players');
            const players = await res.json();
            let h = `<h2>قائمة اللاعبين</h2><div style="max-height:400px; overflow-y:auto;">`;
            players.forEach(p => {
                h += `<div class="score-item">
                    <div style="text-align:right">
                        <b>${p.player_name}</b> (@${p.username_key})<br>
                        <small>الفوز الإجمالي: ${p.total_wins || 0}</small>
                    </div>
                </div>`;
            });
            h += `</div><button onclick="showAdminDashboard()">رجوع</button>`;
            document.getElementById('main-ui').innerHTML = `<div class="card">${h}</div>`;
        }

        async function adminManageCategories() {
            const res = await fetch('/api/categories');
            const cats = await res.json();
            let h = `<h2>الفئات (الأنواع)</h2>
                <div id="cat-form" style="background:rgba(0,0,0,0.2); padding:15px; border-radius:15px; margin-bottom:20px;">
                    <h3 id="form-title">إضافة فئة جديدة</h3>
                    <input id="cat_id" type="hidden">
                    <input id="cat_name" placeholder="اسم الفئة">
                    <div style="text-align:right; margin:10px 0;">
                        <label>صورة الفئة:</label>
                        <input type="file" id="cat_file" accept="image/*" style="padding:10px; background:#0f0c29;">
                    </div>
                    <input id="cat_order" type="number" placeholder="التسلسل (0, 1, 2...)" value="0">
                    <div style="display:flex; gap:10px;">
                        <button id="cat-save-btn" onclick="saveCategory()">حفظ الفئة</button>
                        <button id="cat-cancel-btn" style="background:#636e72; display:none;" onclick="resetCatForm()">إلغاء التعديل</button>
                    </div>
                </div>
                <div style="max-height:400px; overflow-y:auto; text-align:right;">`;
            cats.forEach(c => {
                h += `<div class="score-item" style="flex-direction:column; align-items:flex-start;">
                    <div style="display:flex; justify-content:space-between; width:100%; align-items:center;">
                        <div style="display:flex; align-items:center;">
                            ${c.image_url ? `<img src="${c.image_url}" style="width:40px; height:40px; border-radius:10px; margin-left:10px; object-fit:cover;">` : ''}
                            <div>
                                <b style="font-size:18px;">${c.name}</b>
                                <div style="font-size:12px; color:var(--accent)">الترتيب: ${c.display_order}</div>
                            </div>
                        </div>
                        <div style="display:flex; gap:5px;">
                            <button style="width:auto; padding:5px 10px; margin:0; background:var(--success)" onclick="manageWords('${c.name.replace(/'/g, "\\'")}')">الكلمات</button>
                            <button style="width:auto; padding:5px 10px; margin:0; background:var(--primary)" onclick="editCategory(${JSON.stringify(c).replace(/"/g, '&quot;')})">تعديل</button>
                            <button style="width:auto; padding:5px 10px; margin:0; background:var(--error)" onclick="deleteCategory(${c.id})">حذف</button>
                        </div>
                    </div>
                </div>`;
            });
            h += `</div><button onclick="showAdminDashboard()">رجوع</button>`;
            document.getElementById('main-ui').innerHTML = `<div class="card">${h}</div>`;
        }

        function editCategory(c) {
            document.getElementById('form-title').innerText = "تعديل الفئة: " + c.name;
            document.getElementById('cat_id').value = c.id;
            document.getElementById('cat_name').value = c.name;
            document.getElementById('cat_order').value = c.display_order;
            window.oldCatName = c.name;
            window.editingImage = c.image_url; // حفظ الصورة الحالية
            document.getElementById('cat-cancel-btn').style.display = "block";
            document.getElementById('cat-save-btn').innerText = "تحديث الفئة";
            document.getElementById('cat-form').scrollIntoView();
        }

        function resetCatForm() {
            document.getElementById('form-title').innerText = "إضافة فئة جديدة";
            document.getElementById('cat_id').value = "";
            document.getElementById('cat_name').value = "";
            document.getElementById('cat_order').value = "0";
            document.getElementById('cat_file').value = "";
            document.getElementById('cat-cancel-btn').style.display = "none";
            document.getElementById('cat-save-btn').innerText = "حفظ الفئة";
            window.oldCatName = null;
            window.editingImage = null;
        }

        async function saveCategory() {
            const id = document.getElementById('cat_id').value;
            const name = document.getElementById('cat_name').value;
            const order = document.getElementById('cat_order').value;
            const fileInput = document.getElementById('cat_file');

            if(!name) return alert("الرجاء إدخال اسم الفئة");

            let imageUrl = window.editingImage || null;
            if (fileInput.files.length > 0) {
                imageUrl = await new Promise((resolve) => {
                    const reader = new FileReader();
                    reader.onload = (e) => resolve(e.target.result);
                    reader.readAsDataURL(fileInput.files[0]);
                });
            }

            const endpoint = id ? '/api/admin/category/update' : '/api/admin/category/add';
            const payload = { id, name, display_order: parseInt(order), image_url: imageUrl };
            if (id && window.oldCatName) payload.old_name = window.oldCatName;

            const res = await fetch(endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            if ((await res.json()).success) {
                resetCatForm();
                adminManageCategories();
            }
        }

        async function deleteCategory(id) {
            if(!confirm("هل أنت متأكد من حذف هذه الفئة وكل كلماتها؟")) return;
            await fetch('/api/admin/category/delete', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({id})});
            adminManageCategories();
        }

        async function manageWords(catName) {
            const res = await fetch('/api/admin/words');
            const allWords = await res.json();
            const words = allWords.filter(w => w.category === catName);

            let h = `<h2>كلمات قسم: ${catName}</h2>
                <div style="background:rgba(0,0,0,0.2); padding:15px; border-radius:15px; margin-bottom:20px;">
                    <input id="new_word_val" placeholder="إضافة كلمة جديدة">
                    <button onclick="addWordToCat('${catName.replace(/'/g, "\\'")}')">إضافة للقسم</button>
                </div>
                <div style="max-height:400px; overflow-y:auto; text-align:right;">`;

            if (words.length === 0) {
                h += `<p style="text-align:center; color:#888;">لا توجد كلمات في هذا القسم حالياً</p>`;
            }

            words.forEach(w => {
                h += `<div class="score-item">
                    <span style="font-size:18px;">${w.word}</span>
                    <button style="width:auto; padding:5px 10px; margin:0; background:var(--error)" onclick="deleteWord(${w.id}, '${catName.replace(/'/g, "\\'")}')">حذف</button>
                </div>`;
            });
            h += `</div><button onclick="adminManageCategories()">رجوع للفئات</button>`;
            document.getElementById('main-ui').innerHTML = `<div class="card">${h}</div>`;
        }

        async function addWordToCat(cat) {
            const word = document.getElementById('new_word_val').value;
            if(!word) return;
            await fetch('/api/admin/add_word', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({category: cat, word})});
            manageWords(cat);
        }

        async function deleteWord(id, cat) {
            await fetch('/api/admin/word/delete', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({id})});
            manageWords(cat);
        }

        async function showReports() {
            toggleSidebar();
            // تحديث بيانات المستخدم للحصول على أحدث النقاط للاعبين المحليين
            const resAuth = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: currentUser.username_key, password: currentUser.password_key})
            });
            const dAuth = await resAuth.json();
            if(dAuth.success) {
                currentUser = dAuth.user;
                localStorage.setItem('user', JSON.stringify(currentUser));
            }

            let players = (currentUser.saved_players || []).map(p => typeof p === 'string' ? {name: p, wins: 0} : p);
            players.sort((a, b) => (b.wins || 0) - (a.wins || 0));

            let h = `<h2>📊 تقارير لاعبيك المحليين</h2>
                <p style="font-size:14px; color:#aaa;">ترتيب اللاعبين الذين أضفتهم حسب عدد مرات الفوز</p>
                <div style="max-height:400px; overflow-y:auto; margin:15px 0;">`;

            players.forEach((p, i) => {
                let medal = "";
                if(i === 0 && p.wins > 0) medal = "👑 ";
                h += `<div class="score-item" style="border-left: 4px solid ${i<3 ? 'var(--accent)' : '#333'}">
                    <div style="text-align:right">
                        <b>${medal}${p.name}</b>
                    </div>
                    <div style="text-align:left">
                        <b style="color:var(--success)">${p.wins || 0}</b> <small>فوز</small>
                    </div>
                </div>`;
            });

            if(players.length === 0) h += `<p style="padding:20px;">لم تقم بإضافة أي لاعبين محليين بعد.</p>`;

            if(players.length > 0) {
                const least = players[players.length - 1];
                h += `<div style="margin-top:20px; padding:10px; background:rgba(235, 77, 75, 0.1); border-radius:15px; font-size:14px;">
                    🐢 الأقل فوزاً حالياً: <b>${least.name}</b>
                </div>`;
            }

            h += `</div><button onclick="showMenu()">رجوع</button>`;
            document.getElementById('main-ui').innerHTML = `<div class="card">${h}</div>`;
        }
        function logout() { localStorage.clear(); location.reload(); }

        const sounds = {
            click: new Audio('https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3'),
            reveal: new Audio('https://assets.mixkit.co/active_storage/sfx/2018/2018-preview.mp3'),
            win: new Audio('https://assets.mixkit.co/active_storage/sfx/2013/2013-preview.mp3')
        };
        function playSound(name) { sounds[name].currentTime = 0; sounds[name].play().catch(()=>null); }

        // PWA Registration and Install Prompt
        let deferredPrompt;
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/sw.js')
                    .then(reg => console.log('SW Registered', reg))
                    .catch(err => console.log('SW Failed', err));
            });
        }

        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            showInstallBanner();
        });

        function showInstallBanner() {
            if (document.getElementById('install-banner')) return;
            const banner = document.createElement('div');
            banner.id = 'install-banner';
            banner.style = "position:fixed; bottom:20px; left:20px; right:20px; background:var(--primary); padding:15px; border-radius:15px; display:flex; justify-content:space-between; align-items:center; z-index:2000; box-shadow: 0 5px 15px rgba(0,0,0,0.5);";
            banner.innerHTML = `
                <span style="font-weight:bold;">ثبت التطبيق لتجربة أفضل! 📱</span>
                <div style="display:flex; gap:10px;">
                    <button onclick="installApp()" style="width:auto; padding:5px 15px; margin:0; background:var(--accent); color:black;">تثبيت</button>
                    <button onclick="this.parentElement.parentElement.remove()" style="width:auto; padding:5px 10px; margin:0; background:rgba(0,0,0,0.2);">إغلاق</button>
                </div>
            `;
            document.body.appendChild(banner);
        }

        async function installApp() {
            if (!deferredPrompt) return;
            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;
            if (outcome === 'accepted') {
                console.log('User accepted install');
            }
            deferredPrompt = null;
            document.getElementById('install-banner').remove();
        }

        init();
    </script>
</body>
</html>
"""
