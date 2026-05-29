import random
import string
from fastapi import APIRouter
from .index import get_db_conn, RealDictCursor

router = APIRouter()

@router.post("/api/domino/create")
async def create_domino_room_endpoint(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        user_id = int(data['user_id'])
        player_name = data['player_name']
        max_players = int(data.get('max_players', 4))
        room_code = ''.join(random.choices(string.ascii_uppercase, k=4))

        with conn.cursor() as cur:
            # التأكد من نوع عمود الفريق
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
        print(f"Error: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@router.post("/api/domino/start")
async def start_domino_game_endpoint(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room: return {"success": False, "msg": "الغرفة غير موجودة"}
            if room['host_id'] != user_id: return {"success": False, "msg": "فقط المضيف يبدأ"}

            cur.execute("SELECT user_id, team FROM room_players WHERE room_code = %s", (room_code,))
            players = cur.fetchall()
            if len(players) not in [2, 4]: return {"success": False, "msg": "العدد يجب أن يكون 2 أو 4"}

            # توزيع الفرق تلقائياً (0 للفريق الأول، 1 للفريق الثاني)
            for i, p in enumerate(players):
                t_val = 0 if i % 2 == 0 else 1
                cur.execute("UPDATE room_players SET team = %s WHERE room_code = %s AND user_id = %s", (t_val, room_code, p['user_id']))

            # توزيع الأحجار
            all_tiles = [[i, j] for i in range(7) for j in range(i, 7)]
            random.shuffle(all_tiles)

            hands = {}
            p_ids = [p['user_id'] for p in players]
            tiles_per_p = 7
            for pid in p_ids:
                hands[str(pid)] = [all_tiles.pop() for _ in range(tiles_per_p)]

            game_data = {
                "hands": hands,
                "boneyard": all_tiles,
                "board": [],
                "turn_index": 0,
                "ordered_ids": p_ids,
                "scores": {"0": 0, "1": 0},
                "phase": "playing"
            }

            cur.execute("UPDATE rooms SET status = 'playing', game_data = %s WHERE room_code = %s", (random.json.dumps(game_data), room_code))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@router.post("/api/domino/play")
async def domino_play_tile(data: dict):
    # (باقي منطق اللعب ينتقل هنا بنفس الطريقة)
    return {"success": True}
