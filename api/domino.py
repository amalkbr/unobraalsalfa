import random
import string
import json
from fastapi import APIRouter
from .database import get_db, RealDictCursor

router = APIRouter()

def get_standard_deck():
    # 28 قطعة دومينو من [0,0] إلى [6,6]
    return [[i, j] for i in range(7) for j in range(i, 7)]

@router.post("/api/domino/create")
async def create_domino_room_endpoint(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False, "msg": "خطأ في الاتصال بقاعدة البيانات"}
        try:
            user_id = int(data['user_id'])
            player_name = data['player_name']
            max_players = int(data.get('max_players', 4))
            room_code = ''.join(random.choices(string.ascii_uppercase, k=4))

            with conn.cursor() as cur:
                # التحقق من نوع عمود الفريق (نصي أم رقمي) لضمان التوافق
                cur.execute("SELECT data_type FROM information_schema.columns WHERE table_name = 'room_players' AND column_name = 'team'")
                team_col = cur.fetchone()
                team_val = 0 if team_col and 'int' in team_col[0].lower() else 'A'

                cur.execute("""
                    INSERT INTO rooms (room_code, room_id, host_id, creator_id, status, game_type, win_limit, max_players)
                    VALUES (%s, %s, %s, %s, 'lobby', 'domino', 101, %s)
                """, (room_code, room_code, user_id, user_id, max_players))

                cur.execute("""
                    INSERT INTO room_players (room_code, room_id, user_id, player_name, join_order, team)
                    VALUES (%s, %s, %s, %s, 0, %s)
                """, (room_code, room_code, user_id, player_name, team_val))

                conn.commit()
            return {"success": True, "room_code": room_code}
        except Exception as e:
            return {"success": False, "msg": str(e)}

@router.post("/api/domino/set_team")
async def set_domino_team(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False}
        try:
            room_code = data['room_code'].upper()
            user_id = int(data['user_id'])
            team = data['team']

            with conn.cursor() as cur:
                cur.execute("UPDATE room_players SET team = %s WHERE room_code = %s AND user_id = %s", (team, room_code, user_id))
                conn.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "msg": str(e)}

@router.post("/api/domino/start")
async def start_domino_game_endpoint(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False, "msg": "فشل الاتصال"}
        try:
            room_code = data['room_code'].upper()
            user_id = int(data['user_id'])

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # قفل الغرفة للتعديل (FOR UPDATE) لمنع تضارب العمليات
                cur.execute("SELECT host_id, game_type FROM rooms WHERE room_code = %s FOR UPDATE", (room_code,))
                room = cur.fetchone()
                if not room or room['game_type'] != 'domino':
                    return {"success": False, "msg": "الغرفة غير موجودة"}
                if room['host_id'] != user_id:
                    return {"success": False, "msg": "المضيف فقط يبدأ اللعبة"}

                cur.execute("SELECT user_id, player_name, team FROM room_players WHERE room_code = %s ORDER BY join_order", (room_code,))
                players = cur.fetchall()
                n = len(players)

                if n not in [2, 4]:
                    return {"success": False, "msg": "العدد المطلوب 2 أو 4 لاعبين"}

                # توزيع الفرق وترتيب اللاعبين (A1, B1, A2, B2)
                team_a = [p for i, p in enumerate(players) if i % 2 == 0]
                team_b = [p for i, p in enumerate(players) if i % 2 != 0]

                for p in team_a:
                    cur.execute("UPDATE room_players SET team = %s WHERE room_code = %s AND user_id = %s", (0, room_code, p['user_id']))
                for p in team_b:
                    cur.execute("UPDATE room_players SET team = %s WHERE room_code = %s AND user_id = %s", (1, room_code, p['user_id']))

                ordered_players = [team_a[0], team_b[0]]
                if n == 4: ordered_players += [team_a[1], team_b[1]]

                p_ids = [p['user_id'] for p in ordered_players]
                all_tiles = get_standard_deck()
                random.shuffle(all_tiles)

                # توزيع 7 قطع لكل لاعب
                hands = {str(pid): [all_tiles.pop() for _ in range(7)] for pid in p_ids}

                # تحديد صاحب البداية (أكبر قطعة مزدوجة)
                starter_index = 0
                max_double = -1
                for i, pid in enumerate(p_ids):
                    for tile in hands[str(pid)]:
                        if tile[0] == tile[1] and tile[0] > max_double:
                            max_double = tile[0]; starter_index = i

                game_data = {
                    "hands": hands, "boneyard": all_tiles, "board": [],
                    "turn_index": starter_index, "ordered_ids": p_ids,
                    "scores": {"0": 0, "1": 0}, "phase": "playing", "round_count": 1
                }

                cur.execute("UPDATE rooms SET status = 'playing', game_data = %s WHERE room_code = %s",
                            (json.dumps(game_data), room_code))
                conn.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "msg": str(e)}

@router.post("/api/domino/draw")
async def domino_draw_tile(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False}
        try:
            room_code = data['room_code'].upper(); user_id = int(data['user_id'])
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT game_data FROM rooms WHERE room_code = %s FOR UPDATE", (room_code,))
                room = cur.fetchone()
                if not room: return {"success": False, "msg": "الغرفة غير موجودة"}

                game_data = room['game_data']
                if isinstance(game_data, str): game_data = json.loads(game_data)

                if game_data['ordered_ids'][game_data['turn_index']] != user_id:
                    return {"success": False, "msg": "ليس دورك"}

                boneyard = game_data.get('boneyard', [])
                if not boneyard:
                    # تمرير الدور إذا خلصت القطع
                    game_data['turn_index'] = (game_data['turn_index'] + 1) % len(game_data['ordered_ids'])
                    cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                    conn.commit()
                    return {"success": True, "msg": "لا توجد قطع، تم تمرير الدور"}

                tile = boneyard.pop()
                uid_str = str(user_id)
                if uid_str not in game_data['hands']: game_data['hands'][uid_str] = []
                game_data['hands'][uid_str].append(tile)
                game_data['boneyard'] = boneyard

                cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                conn.commit()
            return {"success": True, "tile": tile}
        except Exception as e:
            return {"success": False, "msg": str(e)}

@router.post("/api/domino/play")
async def domino_play_tile(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False}
        try:
            room_code = data['room_code'].upper(); user_id = int(data['user_id'])
            tile = data['tile']; side = data.get('side', 'right')

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT game_data, status, win_limit FROM rooms WHERE room_code = %s FOR UPDATE", (room_code,))
                room = cur.fetchone()
                if not room or room['status'] != 'playing': return {"success": False, "msg": "اللعبة غير جارية"}

                game_data = room['game_data']
                if isinstance(game_data, str): game_data = json.loads(game_data)

                if game_data['ordered_ids'][game_data['turn_index']] != user_id:
                    return {"success": False, "msg": "ليس دورك"}

                hand = game_data['hands'][str(user_id)]
                # التأكد من وجود القطعة في يد اللاعب
                tile_idx = -1
                for i, t in enumerate(hand):
                    if sorted(t) == sorted(tile):
                        tile_idx = i; break

                if tile_idx == -1: return {"success": False, "msg": "لا تملك هذه القطعة"}

                board = game_data['board']
                if not board: board.append(tile)
                else:
                    left_v, right_v = board[0][0], board[-1][1]
                    if side == 'left':
                        if tile[1] == left_v: board.insert(0, tile)
                        elif tile[0] == left_v: board.insert(0, [tile[1], tile[0]])
                        else: return {"success": False, "msg": "القطعة لا تطابق الطرف"}
                    else:
                        if tile[0] == right_v: board.append(tile)
                        elif tile[1] == right_v: board.append([tile[1], tile[0]])
                        else: return {"success": False, "msg": "القطعة لا تطابق الطرف"}

                hand.pop(tile_idx)

                # التحقق من نهاية الجولة
                if not hand:
                    game_data['phase'] = 'round_end'
                    cur.execute("SELECT team FROM room_players WHERE room_code = %s AND user_id = %s", (room_code, user_id))
                    t_res = cur.fetchone()
                    winner_team = str(t_res['team']) if t_res else "0"

                    total_pips = sum(sum(t) for h in game_data['hands'].values() for t in h)
                    game_data['scores'][winner_team] += total_pips
                    game_data['round_winner_team'] = winner_team
                    game_data['round_points'] = total_pips

                    if game_data['scores'][winner_team] >= (room.get('win_limit') or 101):
                        game_data['phase'] = 'game_over'; cur.execute("UPDATE rooms SET status = 'result' WHERE room_code = %s", (room_code,))
                else:
                    game_data['turn_index'] = (game_data['turn_index'] + 1) % len(game_data['ordered_ids'])
                    # التحقق من القفلة (Stalemate)
                    if not game_data.get('boneyard'):
                        lv, rv = board[0][0], board[-1][1]
                        can_play = any(t[0] in [lv, rv] or t[1] in [lv, rv] for h in game_data['hands'].values() for t in h)
                        if not can_play:
                            game_data['phase'] = 'round_end'
                            cur.execute("SELECT user_id, team FROM room_players WHERE room_code = %s", (room_code,))
                            p_teams = {str(r['user_id']): str(r['team']) for r in cur.fetchall()}
                            t_sums = {"0": 0, "1": 0}
                            for pid, h in game_data['hands'].items(): t_sums[p_teams.get(pid, "0")] += sum(sum(t) for t in h)

                            st_winner = "0" if t_sums["0"] < t_sums["1"] else ("1" if t_sums["1"] < t_sums["0"] else None)
                            if st_winner:
                                total = sum(t_sums.values())
                                game_data['scores'][st_winner] += total
                                game_data['round_winner_team'] = st_winner
                                game_data['round_points'] = total
                                if game_data['scores'][st_winner] >= (room.get('win_limit') or 101):
                                    game_data['phase'] = 'game_over'; cur.execute("UPDATE rooms SET status = 'result' WHERE room_code = %s", (room_code,))
                            else: game_data['round_winner_team'] = None # تعادل كامل

                cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                conn.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "msg": str(e)}

@router.post("/api/domino/next_round")
async def domino_next_round(data: dict):
    with get_db() as conn:
        if not conn: return {"success": False}
        try:
            room_code = data['room_code'].upper(); user_id = int(data['user_id'])
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT host_id, game_data FROM rooms WHERE room_code = %s FOR UPDATE", (room_code,))
                room = cur.fetchone()
                if not room or room['host_id'] != user_id: return {"success": False, "msg": "غير مصرح"}

                game_data = room['game_data']
                if isinstance(game_data, str): game_data = json.loads(game_data)

                p_ids = game_data['ordered_ids']
                all_tiles = get_standard_deck(); random.shuffle(all_tiles)
                game_data.update({
                    "hands": {str(pid): [all_tiles.pop() for _ in range(7)] for pid in p_ids},
                    "boneyard": all_tiles, "board": [], "phase": "playing",
                    "round_count": game_data.get('round_count', 1) + 1
                })
                game_data['turn_index'] = (game_data['round_count'] - 1) % len(p_ids)

                cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                conn.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "msg": str(e)}
