import random
import time
import json
from fastapi import APIRouter
from api.database import get_db, RealDictCursor

router = APIRouter()

async def prepare_round(room_code, conn=None):
    """تجهيز جولة جديدة في لعبة 'برا السالفة'"""
    # إذا لم يتم تمرير اتصال، نفتح واحد جديد
    if conn is None:
        with get_db() as new_conn:
            return await _prepare_round_logic(room_code, new_conn)
    else:
        return await _prepare_round_logic(room_code, conn)

async def _prepare_round_logic(room_code, conn):
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # قفل الغرفة للتعديل
            cur.execute("SELECT category, distribution_mode FROM rooms WHERE room_code = %s FOR UPDATE", (room_code,))
            room = cur.fetchone()
            if not room: return

            cat = room['category']
            cur.execute("SELECT word FROM words WHERE category = %s", (cat,))
            words = [r['word'].strip() for r in cur.fetchall()]
            if not words: words = ["بيتزا", "شاورما", "منسف"]

            correct = random.choice(words)
            cur.execute("SELECT user_id, player_name, red_card FROM room_players WHERE room_code = %s ORDER BY join_order ASC, user_id ASC", (room_code,))
            players = cur.fetchall()

            if not players: return

            spy_idx = random.randint(0, len(players)-1)
            spy_id = players[spy_idx]['user_id']

            cur.execute("UPDATE room_players SET is_ready = FALSE WHERE room_code = %s", (room_code,))

            active_players = [p for p in players if not p['red_card']]
            if len(active_players) < 3: active_players = players

            other = [w for w in words if w != correct]
            guesses = random.sample(other, min(len(other), 6)) + [correct]
            random.shuffle(guesses)

            current_asker = active_players[0]
            auto_seq = []
            p_ids = [p['user_id'] for p in active_players]
            n = len(p_ids)
            for shift in range(1, n):
                for i in range(n):
                    auto_seq.append({'asker_id': p_ids[i], 'ans_id': p_ids[(i + shift) % n]})

            dist_mode = room.get('distribution_mode', 'auto')
            game_data = {
                "word": correct, "spy_id": spy_id, "q_seq": [], "auto_seq": auto_seq,
                "current_seq_idx": 0, "distribution_mode": dist_mode,
                "current_asker_id": current_asker['user_id'], "current_asker_name": current_asker['player_name'],
                "ready_to_vote": [], "current_q": None, "guesses": guesses, "messages": [],
                "phase_start": time.time(), "phase_timeout": 0
            }

            cur.execute("UPDATE rooms SET status = 'roles_prep', secret_word = %s, spy_id = %s, game_data = %s WHERE room_code = %s",
                        (correct, spy_id, json.dumps(game_data), room_code))
            conn.commit()
    except Exception as e:
        print(f"Error in prepare_round: {e}")
        conn.rollback()

async def calculate_online_results(room_code, conn=None):
    if conn is None:
        with get_db() as new_conn:
            return await _calculate_logic(room_code, new_conn)
    else:
        return await _calculate_logic(room_code, conn)

async def _calculate_logic(room_code, conn):
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM rooms WHERE room_code = %s FOR UPDATE", (room_code,))
            room = cur.fetchone()
            if not room: return

            game_data = room['game_data']
            spy_id = room['spy_id']
            votes = game_data.get('votes', {})

            vote_counts = {}
            for v_id_str, target_id in votes.items():
                tid = int(target_id)
                vote_counts[tid] = vote_counts.get(tid, 0) + 1

            max_votes = -1
            voted_out_id = None
            for p_id, count in vote_counts.items():
                if count > max_votes: max_votes = count; voted_out_id = p_id
                elif count == max_votes: voted_out_id = None

            spy_caught = (voted_out_id == spy_id)
            game_data['spy_caught'] = spy_caught

            for v_id_str, target_id in votes.items():
                if int(target_id) == spy_id:
                    cur.execute("UPDATE room_players SET score = score + 1 WHERE room_code = %s AND user_id = %s AND red_card = FALSE", (room_code, int(v_id_str)))

            if not spy_caught:
                cur.execute("UPDATE room_players SET score = score + 1 WHERE room_code = %s AND user_id = %s AND red_card = FALSE", (room_code, spy_id))

            cur.execute("SELECT user_id, score FROM room_players WHERE room_code = %s", (room_code,))
            players_scores = cur.fetchall()

            game_over = False
            winner_id = None
            for p in players_scores:
                if p['score'] >= (room['win_limit'] or 5):
                    game_over = True; winner_id = p['user_id']; break

            if game_over:
                game_data['game_over'] = True; game_data['winner_id'] = winner_id
                cur.execute("UPDATE users SET online_points = online_points + 1 WHERE user_id = %s", (winner_id,))
                cur.execute("UPDATE rooms SET status = 'result', game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
            else:
                game_data['phase_start'] = time.time()
                cur.execute("UPDATE rooms SET status = 'spy_reveal', game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))

            conn.commit()
    except Exception as e:
        print(f"Error in calculate_results: {e}")
        conn.rollback()

@router.post("/api/online/create")
async def create_room(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False, "msg": "DB Error"}
        try:
            user_id = int(data.get('user_id'))
            player_name = str(data.get('player_name', 'لاعب'))[:100]
            category = str(data.get('category', 'أكلات'))
            win_limit = int(data.get('win_limit', 10))
            room_code = None
            with conn.cursor() as cur:
                cur.execute("INSERT INTO users (user_id, player_name, is_registered) VALUES (%s, %s, TRUE) ON CONFLICT (user_id) DO UPDATE SET player_name = EXCLUDED.player_name", (user_id, player_name))
                for _ in range(5):
                    candidate = ''.join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=5))
                    cur.execute("SELECT 1 FROM rooms WHERE room_code = %s", (candidate,))
                    if not cur.fetchone(): room_code = candidate; break
                if not room_code: return {"success": False, "msg": "Code Gen Error"}
                cur.execute("INSERT INTO rooms (room_code, room_id, host_id, creator_id, status, category, win_limit, game_type) VALUES (%s, %s, %s, %s, 'waiting', %s, %s, 'spy')", (room_code, room_code, user_id, user_id, category, win_limit))
                cur.execute("INSERT INTO room_players (room_code, room_id, user_id, player_name, is_ready, join_order, score, vote_limit, vote_cat) VALUES (%s, %s, %s, %s, TRUE, 1, 0, %s, %s)", (room_code, room_code, user_id, player_name, win_limit, category))
                conn.commit()
            return {"success": True, "room_code": room_code}
        except Exception as e: return {"success": False, "msg": str(e)}

@router.post("/api/online/join")
async def join_room(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False, "msg": "DB Error"}
        try:
            room_code = data['room_code'].upper()
            user_id = int(data['user_id'])
            player_name = data['player_name']
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT status, game_type, max_players FROM rooms WHERE room_code = %s FOR UPDATE", (room_code,))
                room = cur.fetchone()
                if not room: return {"success": False, "msg": "Room not found"}

                status = room['status']
                is_open = (status == 'waiting' or status == 'lobby')

                cur.execute("SELECT join_order FROM room_players WHERE room_code = %s AND user_id = %s", (room_code, user_id))
                row = cur.fetchone()
                if not row and not is_open: return {"success": False, "msg": "Started"}

                if not row:
                    cur.execute("SELECT COUNT(*) as count FROM room_players WHERE room_code = %s", (room_code,))
                    if cur.fetchone()['count'] >= (room.get('max_players') or 10): return {"success": False, "msg": "Full"}
                    cur.execute("SELECT COALESCE(MAX(join_order), 0) + 1 as next_order FROM room_players WHERE room_code = %s", (room_code,))
                    next_order = cur.fetchone()['next_order']
                    cur.execute("INSERT INTO room_players (room_id, room_code, user_id, player_name, join_order, is_ready) VALUES (%s, %s, %s, %s, %s, TRUE)", (room_code, room_code, user_id, player_name, next_order))
                else:
                    cur.execute("UPDATE room_players SET player_name = %s WHERE room_code = %s AND user_id = %s", (player_name, room_code, user_id))
                conn.commit()
            return {"success": True}
        except Exception as e: return {"success": False, "msg": str(e)}

@router.post("/api/online/leave")
async def leave_online_room(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False}
        try:
            room_code = data['room_code'].upper(); user_id = int(data['user_id'])
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("DELETE FROM room_players WHERE room_code = %s AND user_id = %s", (room_code, user_id))
                cur.execute("SELECT user_id FROM room_players WHERE room_code = %s ORDER BY join_order ASC", (room_code,))
                rem = cur.fetchall()
                if not rem: cur.execute("DELETE FROM rooms WHERE room_code = %s", (room_code,))
                else:
                    cur.execute("SELECT host_id FROM rooms WHERE room_code = %s FOR UPDATE", (room_code,))
                    if cur.fetchone()['host_id'] == user_id: cur.execute("UPDATE rooms SET host_id = %s WHERE room_code = %s", (rem[0]['user_id'], room_code))
                conn.commit()
            return {"success": True}
        except: return {"success": False}

@router.post("/api/online/start")
async def start_online_game(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False}
        try:
            room_code = data['room_code'].upper()
            user_id = int(data['user_id'])
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT host_id FROM rooms WHERE room_code = %s FOR UPDATE", (room_code,))
                room = cur.fetchone()
                if not room or room['host_id'] != user_id: return {"success": False}

                cur.execute("SELECT COUNT(*) FROM room_players WHERE room_code = %s", (room_code,))
                if cur.fetchone()['count'] < 3: return {"success": False, "msg": "عدد اللاعبين غير كافٍ"}

                cur.execute("SELECT vote_limit, COUNT(*) as c FROM room_players WHERE room_code = %s AND vote_limit IS NOT NULL GROUP BY vote_limit ORDER BY c DESC LIMIT 1", (room_code,))
                rl = cur.fetchone()
                cur.execute("SELECT vote_cat, COUNT(*) as c FROM room_players WHERE room_code = %s AND vote_cat IS NOT NULL GROUP BY vote_cat ORDER BY c DESC LIMIT 1", (room_code,))
                rc = cur.fetchone()

                cur.execute("UPDATE rooms SET win_limit = %s, category = %s, status = 'roles_prep' WHERE room_code = %s", (rl['vote_limit'] if rl else 10, rc['vote_cat'] if rc else "أكلات", room_code))
                # نقوم بالتجهيز داخل نفس الاتصال
                await prepare_round(room_code, conn=conn)
                conn.commit()
            return {"success": True}
        except Exception as e: return {"success": False, "msg": str(e)}

@router.post("/api/online/submit_vote")
async def submit_vote(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False}
        try:
            room_code = data['room_code'].upper(); user_id = int(data['user_id'])
            vtype = data['type']; val = data['value']; is_lobby = data.get('is_lobby', False)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT status, game_data FROM rooms WHERE room_code = %s FOR UPDATE", (room_code,))
                room = cur.fetchone()

                if vtype == 'limit': cur.execute("UPDATE room_players SET vote_limit = %s WHERE room_code = %s AND user_id = %s", (int(val), room_code, user_id))
                else: cur.execute("UPDATE room_players SET vote_cat = %s WHERE room_code = %s AND user_id = %s", (val, room_code, user_id))

                if not is_lobby:
                    cur.execute(f"SELECT COUNT(*) FROM room_players WHERE room_code = %s AND vote_{vtype} IS NULL", (room_code,))
                    if cur.fetchone()['count'] == 0:
                        cur.execute(f"SELECT vote_{vtype}, COUNT(*) as c FROM room_players WHERE room_code = %s GROUP BY vote_{vtype} ORDER BY c DESC LIMIT 1", (room_code,))
                        winner = cur.fetchone()[0]
                        if vtype == 'limit':
                            gd = room['game_data'] or {}; gd['phase_start'] = time.time()
                            cur.execute("UPDATE rooms SET win_limit = %s, status = 'voting_cat', game_data = %s WHERE room_code = %s", (winner, json.dumps(gd), room_code))
                        else:
                            cur.execute("UPDATE rooms SET category = %s, status = 'roles_prep' WHERE room_code = %s", (winner, room_code))
                            await prepare_round(room_code, conn=conn)
                conn.commit()
            return {"success": True}
        except Exception as e: return {"success": False, "msg": str(e)}

@router.get("/api/online/room/{room_code}")
async def get_room(room_code: str):
    with get_db() as conn:
        if not conn: return {"success": False}
        try:
            room_code = room_code.upper()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM rooms WHERE room_code = %s FOR UPDATE", (room_code,))
                room = cur.fetchone()
                if not room: return {"success": False}

                cur.execute("UPDATE rooms SET updated_at = CURRENT_TIMESTAMP WHERE room_code = %s", (room_code,))

                gd = room['game_data'] or {}
                ps = gd.get('phase_start')
                changed = False
                if ps and (time.time() - ps > 20): # زيادة الوقت قليلاً للتأكد
                    if room['status'] == 'voting_limit':
                        gd['phase_start'] = time.time()
                        cur.execute("UPDATE rooms SET status = 'voting_cat', game_data = %s WHERE room_code = %s", (json.dumps(gd), room_code)); changed = True
                    elif room['status'] == 'voting_cat':
                        cur.execute("UPDATE rooms SET status = 'roles_prep' WHERE room_code = %s", (room_code,)); changed = True
                        await prepare_round(room_code, conn=conn)
                    elif room['status'] == 'voting_spy':
                        await calculate_online_results(room_code, conn=conn); changed = True

                if changed:
                    cur.execute("SELECT * FROM rooms WHERE room_code = %s", (room_code,))
                    room = cur.fetchone()

                cur.execute("SELECT user_id, player_name, is_ready, score, yellow_cards, red_card, vote_limit, vote_cat FROM room_players WHERE room_code = %s ORDER BY join_order ASC", (room_code,))
                players = cur.fetchall()
                conn.commit()
            return {"success": True, "room": room, "players": players}
        except Exception as e:
            print(f"Error in get_room: {e}")
            return {"success": False}

@router.post("/api/online/action")
async def online_action(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False}
        try:
            room_code = data['room_code'].upper(); user_id = int(data['user_id']); action = data['action']
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM rooms WHERE room_code = %s FOR UPDATE", (room_code,))
                room = cur.fetchone(); gd = room['game_data']

                if action == "ready_role":
                    cur.execute("UPDATE room_players SET is_ready = TRUE WHERE room_code = %s AND user_id = %s", (room_code, user_id))
                    cur.execute("SELECT COUNT(*) FROM room_players WHERE room_code = %s AND is_ready = FALSE", (room_code,))
                    if cur.fetchone()['count'] == 0:
                        gd['phase_start'] = time.time(); cur.execute("UPDATE rooms SET status = 'playing_questions', game_data = %s WHERE room_code = %s", (json.dumps(gd), room_code))
                        cur.execute("UPDATE room_players SET is_ready = FALSE WHERE room_code = %s", (room_code,))
                elif action == "choose_target":
                    if not gd.get('current_q'):
                        gd['current_q'] = {"asker_id": user_id, "ans_id": int(data['target_id']), "ans_name": data['target_name'], "status": "asking"}
                        gd['phase_start'] = time.time()
                elif action == "submit_question":
                    cq = gd.get('current_q')
                    if cq and cq['asker_id'] == user_id: cq['question'] = data['text']; cq['status'] = 'answering'; gd['phase_start'] = time.time()
                elif action == "submit_answer":
                    cq = gd.get('current_q')
                    if cq and cq['ans_id'] == user_id:
                        cq['answer'] = data['text']
                        cq['status'] = 'done'
                        if 'q_seq' not in gd: gd['q_seq'] = []
                        gd['q_seq'].append(cq)
                        gd['current_asker_id'] = cq['ans_id']
                        gd['current_asker_name'] = cq.get('ans_name', 'لاعب')
                        gd['current_q'] = None
                        gd['phase_start'] = time.time()
                elif action == "start_voting":
                    if room['host_id'] == user_id:
                        cur.execute("UPDATE rooms SET status = 'voting_spy' WHERE room_code = %s", (room_code,))
                        cur.execute("UPDATE room_players SET is_ready = FALSE WHERE room_code = %s", (room_code,))
                        gd['phase_start'] = time.time()
                elif action == "vote":
                    if 'votes' not in gd: gd['votes'] = {}
                    gd['votes'][str(user_id)] = int(data['target_id'])
                    cur.execute("UPDATE room_players SET is_ready = TRUE WHERE room_code = %s AND user_id = %s", (room_code, user_id))
                    cur.execute("SELECT COUNT(*) FROM room_players WHERE room_code = %s AND is_ready = FALSE AND red_card = FALSE", (room_code,))
                    if cur.fetchone()['count'] == 0: await calculate_online_results(room_code, conn=conn)
                elif action == "spy_guess":
                    if data['guess'] == room['secret_word']:
                        cur.execute("UPDATE room_players SET score = score + 1 WHERE room_code = %s AND user_id = %s", (room_code, user_id))

                    cur.execute("SELECT user_id, score FROM room_players WHERE room_code = %s", (room_code,))
                    players_scores = cur.fetchall()
                    game_over = False; winner_id = None
                    for p in players_scores:
                        if p['score'] >= (room['win_limit'] or 5):
                            game_over = True; winner_id = p['user_id']; break

                    if game_over:
                        gd['game_over'] = True; gd['winner_id'] = winner_id
                        cur.execute("UPDATE users SET online_points = online_points + 1 WHERE user_id = %s", (winner_id,))
                        cur.execute("UPDATE rooms SET status = 'result' WHERE room_code = %s", (room_code,))
                    else:
                        cur.execute("UPDATE rooms SET status = 'result' WHERE room_code = %s", (room_code,))
                elif action == "new_round":
                    if room['host_id'] == user_id: await prepare_round(room_code, conn=conn)

                cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(gd), room_code))
                conn.commit()
            return {"success": True}
        except Exception as e:
            print(f"Error in online_action: {e}")
            return {"success": False}
