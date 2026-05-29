import random
import string
import json
from fastapi import APIRouter
from .database import get_db_conn, RealDictCursor

router = APIRouter()

def get_standard_deck():
    # 28 tiles: [0,0] to [6,6]
    return [[i, j] for i in range(7) for j in range(i, 7)]

@router.post("/api/domino/create")
async def create_domino_room_endpoint(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection error"}
    try:
        user_id = int(data['user_id'])
        player_name = data['player_name']
        max_players = int(data.get('max_players', 4))
        room_code = ''.join(random.choices(string.ascii_uppercase, k=4))

        with conn.cursor() as cur:
            # Check team column type
            cur.execute("SELECT data_type FROM information_schema.columns WHERE table_name = 'room_players' AND column_name = 'team'")
            team_col = cur.fetchone()
            # If it's integer, use 0/1. If text, use 'A'/'B'.
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
        print(f"Error creating domino room: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@router.post("/api/domino/set_team")
async def set_domino_team(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])
        team = data['team'] # 0 or 1 (or 'A'/'B')

        with conn.cursor() as cur:
            cur.execute("UPDATE room_players SET team = %s WHERE room_code = %s AND user_id = %s", (team, room_code, user_id))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@router.post("/api/domino/start")
async def start_domino_game_endpoint(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection error"}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT host_id, game_type FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room or room['game_type'] != 'domino':
                return {"success": False, "msg": "الغرفة غير موجودة"}
            if room['host_id'] != user_id:
                return {"success": False, "msg": "المضيف فقط يمكنه بدء اللعبة"}

            cur.execute("SELECT user_id, player_name, team FROM room_players WHERE room_code = %s ORDER BY join_order", (room_code,))
            players = cur.fetchall()
            n = len(players)

            if n not in [2, 4]:
                return {"success": False, "msg": "يجب أن يكون عدد اللاعبين 2 أو 4"}

            # Auto-assign teams if not set
            team_a = [p for i, p in enumerate(players) if i % 2 == 0]
            team_b = [p for i, p in enumerate(players) if i % 2 != 0]

            # Update teams to ensure consistency (using 0 and 1)
            for p in team_a:
                cur.execute("UPDATE room_players SET team = %s WHERE room_code = %s AND user_id = %s", (0, room_code, p['user_id']))
            for p in team_b:
                cur.execute("UPDATE room_players SET team = %s WHERE room_code = %s AND user_id = %s", (1, room_code, p['user_id']))

            # Order: A1, B1, A2, B2
            if n == 4:
                ordered_players = [team_a[0], team_b[0], team_a[1], team_b[1]]
            else:
                ordered_players = [team_a[0], team_b[0]]

            p_ids = [p['user_id'] for p in ordered_players]

            # Generate and distribute 28 tiles
            all_tiles = get_standard_deck()
            random.shuffle(all_tiles)

            hands = {}
            for pid in p_ids:
                hands[str(pid)] = [all_tiles.pop() for _ in range(7)]

            # Find who starts (highest double)
            starter_index = 0
            max_double = -1
            for i, pid in enumerate(p_ids):
                for tile in hands[str(pid)]:
                    if tile[0] == tile[1] and tile[0] > max_double:
                        max_double = tile[0]
                        starter_index = i

            game_data = {
                "hands": hands,
                "boneyard": all_tiles, # This will have 14 tiles if 2 players, 0 if 4 players
                "board": [],
                "turn_index": starter_index,
                "ordered_ids": p_ids,
                "scores": {"0": 0, "1": 0},
                "phase": "playing",
                "round_count": 1
            }

            cur.execute("UPDATE rooms SET status = 'playing', game_data = %s WHERE room_code = %s",
                        (json.dumps(game_data), room_code))
            conn.commit()

        return {"success": True}
    except Exception as e:
        print(f"Error starting domino: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@router.post("/api/domino/draw")
async def domino_draw_tile(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT game_data FROM rooms WHERE room_code = %s FOR UPDATE", (room_code,))
            room = cur.fetchone()
            if not room: return {"success": False, "msg": "الغرفة غير موجودة"}

            game_data = room['game_data']
            if isinstance(game_data, str): game_data = json.loads(game_data)

            if game_data['ordered_ids'][game_data['turn_index']] != user_id:
                return {"success": False, "msg": "ليس دورك"}

            if game_data.get('phase') != 'playing':
                return {"success": False, "msg": "اللعبة متوقفة حالياً"}

            boneyard = game_data.get('boneyard', [])
            if len(boneyard) == 0:
                # إذا انتهت الأحجار، يمر الدور للاعب التالي
                game_data['turn_index'] = (game_data['turn_index'] + 1) % len(game_data['ordered_ids'])
                cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                conn.commit()
                return {"success": True, "msg": "انتهت الأحجار، تم تمرير الدور"}

            # سحب حجر
            tile = boneyard.pop()

            # التأكد من أن المفتاح نصي وأن القائمة موجودة
            uid_str = str(user_id)
            if uid_str not in game_data['hands']:
                game_data['hands'][uid_str] = []

            game_data['hands'][uid_str].append(tile)
            game_data['boneyard'] = boneyard

            # حفظ التغييرات فوراً
            cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
            conn.commit()
        return {"success": True, "tile": tile} # نرسل الحجر المسحوب للتأكيد
    except Exception as e:
        print(f"Draw Error: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@router.post("/api/domino/play")
async def domino_play_tile(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])
        tile = data['tile'] # [a, b]
        side = data.get('side', 'right') # 'left' or 'right'

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT game_data, status FROM rooms WHERE room_code = %s FOR UPDATE", (room_code,))
            room = cur.fetchone()
            if not room or room['status'] != 'playing': return {"success": False, "msg": "اللعبة ليست جارية"}

            game_data = room['game_data']
            if isinstance(game_data, str): game_data = json.loads(game_data)

            if game_data['ordered_ids'][game_data['turn_index']] != user_id:
                return {"success": False, "msg": "ليس دورك"}

            hand = game_data['hands'][str(user_id)]
            # Check if player has tile (either [a,b] or [b,a])
            tile_to_remove = None
            for t in hand:
                if (t[0] == tile[0] and t[1] == tile[1]) or (t[0] == tile[1] and t[1] == tile[0]):
                    tile_to_remove = t
                    break

            if not tile_to_remove:
                return {"success": False, "msg": "لا تملك هذا الحجر"}

            board = game_data['board']
            if not board:
                board.append(tile)
            else:
                left_val = board[0][0]
                right_val = board[-1][1]

                if side == 'left':
                    if tile[1] == left_val:
                        board.insert(0, tile)
                    elif tile[0] == left_val:
                        board.insert(0, [tile[1], tile[0]])
                    else: return {"success": False, "msg": "الحجر لا يطابق الطرف الأيسر"}
                else: # right
                    if tile[0] == right_val:
                        board.append(tile)
                    elif tile[1] == right_val:
                        board.append([tile[1], tile[0]])
                    else: return {"success": False, "msg": "الحجر لا يطابق الطرف الأيمن"}

            # Remove from hand
            hand.remove(tile_to_remove)

            # Round end check (empty hand)
            if not hand:
                game_data['phase'] = 'round_end'
                cur.execute("SELECT team FROM room_players WHERE room_code = %s AND user_id = %s", (room_code, user_id))
                winner_team = str(cur.fetchone()['team'])

                # Score = sum of all other players' hand pips
                total_pips = 0
                for pid, phand in game_data['hands'].items():
                    for t in phand:
                        total_pips += (t[0] + t[1])

                game_data['scores'][winner_team] = game_data['scores'].get(winner_team, 0) + total_pips
            else:
                # Turn change
                game_data['turn_index'] = (game_data['turn_index'] + 1) % len(game_data['ordered_ids'])

                # Check stalemate (no one can move and boneyard empty)
                if not game_data.get('boneyard'):
                    left_val = board[0][0]
                    right_val = board[-1][1]
                    can_anyone_move = False
                    for pid, phand in game_data['hands'].items():
                        for t in phand:
                            if t[0] in [left_val, right_val] or t[1] in [left_val, right_val]:
                                can_anyone_move = True
                                break
                        if can_anyone_move: break

                    if not can_anyone_move:
                        game_data['phase'] = 'round_end'
                        # Find who has least pips
                        player_totals = {pid: sum(t[0]+t[1] for t in phand) for pid, phand in game_data['hands'].items()}
                        min_pips = min(player_totals.values())
                        winner_id = [pid for pid, pips in player_totals.items() if pips == min_pips][0]

                        cur.execute("SELECT team FROM room_players WHERE room_code = %s AND user_id = %s", (room_code, int(winner_id)))
                        st_winner_team = str(cur.fetchone()['team'])

                        all_pips = sum(player_totals.values())
                        game_data['scores'][st_winner_team] = game_data['scores'].get(st_winner_team, 0) + all_pips

            cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
            conn.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error in play_tile: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@router.post("/api/domino/next_round")
async def domino_next_round(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT host_id, game_data FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room: return {"success": False, "msg": "الغرفة غير موجودة"}
            if room['host_id'] != user_id: return {"success": False, "msg": "المضيف فقط يبدأ الجولة"}

            game_data = room['game_data']
            if isinstance(game_data, str): game_data = json.loads(game_data)

            if game_data.get('phase') != 'round_end': return {"success": False, "msg": "الجولة لم تنتهِ"}

            cur.execute("SELECT user_id FROM room_players WHERE room_code = %s ORDER BY join_order", (room_code,))
            players = cur.fetchall()
            # Reuse ordered_ids from game_data if possible
            p_ids = game_data['ordered_ids']

            all_tiles = get_standard_deck()
            random.shuffle(all_tiles)

            hands = {}
            for pid in p_ids:
                hands[str(pid)] = [all_tiles.pop() for _ in range(7)]

            game_data['hands'] = hands
            game_data['boneyard'] = all_tiles
            game_data['board'] = []
            game_data['phase'] = 'playing'
            game_data['round_count'] = game_data.get('round_count', 1) + 1
            game_data['turn_index'] = (game_data['round_count'] - 1) % len(p_ids)

            cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "msg": str(e)}
    finally: conn.close()
