import random
import string
import json
from fastapi import APIRouter
from .database import get_db_conn, RealDictCursor

router = APIRouter()

@router.post("/api/xo/create")
async def create_xo_room_endpoint(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection error"}
    try:
        user_id = int(data['user_id'])
        player_name = data['player_name']
        room_code = ''.join(random.choices(string.ascii_uppercase, k=4))

        with conn.cursor() as cur:
            # التحقق من نوع حقل team
            cur.execute("SELECT data_type FROM information_schema.columns WHERE table_name = 'room_players' AND column_name = 'team'")
            team_col = cur.fetchone()
            team_val = 'X' if team_col and 'char' in team_col[0].lower() else '0'

            # إنشاء الغرفة بنوع xo وحد أقصى لاعبين 2
            cur.execute("""
                INSERT INTO rooms (room_code, room_id, host_id, creator_id, status, game_type, win_limit, max_players)
                VALUES (%s, %s, %s, %s, 'lobby', 'xo', 5, 2)
            """, (room_code, room_code, user_id, user_id, ))

            # إضافة اللاعب المضيف
            cur.execute("""
                INSERT INTO room_players (room_code, room_id, user_id, player_name, join_order, team)
                VALUES (%s, %s, %s, %s, 0, %s)
            """, (room_code, room_code, user_id, player_name, team_val))

            conn.commit()
        return {"success": True, "room_code": room_code}
    except Exception as e:
        print(f"Error creating xo room: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@router.post("/api/xo/start")
async def start_xo_game_endpoint(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection error"}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT host_id, game_type FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room or room['game_type'] != 'xo':
                return {"success": False, "msg": "الغرفة غير موجودة"}
            if room['host_id'] != user_id:
                return {"success": False, "msg": "المضيف فقط يمكنه بدء اللعبة"}

            cur.execute("SELECT user_id, player_name FROM room_players WHERE room_code = %s ORDER BY join_order", (room_code,))
            players = cur.fetchall()
            n = len(players)

            if n != 2:
                return {"success": False, "msg": "يجب أن يكون عدد اللاعبين 2 للعب إكس أو"}

            p_ids = [p['user_id'] for p in players]
            
            # تعيين الرموز عشوائياً
            symbols = {}
            if random.choice([True, False]):
                symbols[str(p_ids[0])] = "X"
                symbols[str(p_ids[1])] = "O"
                starter_index = 0  # X يبدأ أولاً دائماً
            else:
                symbols[str(p_ids[0])] = "O"
                symbols[str(p_ids[1])] = "X"
                starter_index = 1

            game_data = {
                "board": [""] * 9, # لوحة اللعب 3x3 فارغة
                "scores": {"X": 0, "O": 0},
                "turn_index": starter_index,
                "ordered_ids": p_ids,
                "symbols": symbols,
                "phase": "playing",
                "round_count": 1,
                "winner_id": None
            }

            cur.execute("UPDATE rooms SET status = 'playing', game_data = %s WHERE room_code = %s",
                        (json.dumps(game_data), room_code))
            conn.commit()

        return {"success": True}
    except Exception as e:
        print(f"Error starting xo game: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

def check_win(board):
    win_combinations = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8], # أفقي
        [0, 3, 6], [1, 4, 7], [2, 5, 8], # عمودي
        [0, 4, 8], [2, 4, 6]             # قطري
    ]
    for combo in win_combinations:
        if board[combo[0]] != "" and board[combo[0]] == board[combo[1]] == board[combo[2]]:
            return board[combo[0]]
    return None

@router.post("/api/xo/play")
async def xo_play_move(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection error"}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])
        cell_index = int(data['index']) # من 0 إلى 8

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT game_data, status FROM rooms WHERE room_code = %s FOR UPDATE", (room_code,))
            room = cur.fetchone()
            if not room or room['status'] != 'playing':
                return {"success": False, "msg": "اللعبة ليست جارية"}

            game_data = room['game_data']
            if isinstance(game_data, str): game_data = json.loads(game_data)

            if game_data.get('phase') != 'playing':
                return {"success": False, "msg": "اللعبة متوقفة حالياً"}

            ordered_ids = game_data['ordered_ids']
            turn_index = game_data['turn_index']

            if ordered_ids[turn_index] != user_id:
                return {"success": False, "msg": "ليس دورك"}

            board = game_data['board']
            if board[cell_index] != "":
                return {"success": False, "msg": "هذه الخانة محتلة بالفعل"}

            my_symbol = game_data['symbols'][str(user_id)]
            board[cell_index] = my_symbol

            winner_symbol = check_win(board)
            if winner_symbol:
                # هناك فائز
                game_data['phase'] = 'ended'
                game_data['winner_id'] = user_id
                game_data['scores'][winner_symbol] += 1
            elif "" not in board:
                # تعادل
                game_data['phase'] = 'ended'
                game_data['winner_id'] = 'draw'
            else:
                # تمرير الدور
                game_data['turn_index'] = (turn_index + 1) % len(ordered_ids)

            cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
            conn.commit()

        return {"success": True}
    except Exception as e:
        print(f"Error playing xo move: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@router.post("/api/xo/next_round")
async def xo_next_round(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection error"}
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

            if game_data.get('phase') != 'ended':
                return {"success": False, "msg": "الجولة لم تنتهِ بعد"}

            p_ids = game_data['ordered_ids']
            round_count = game_data.get('round_count', 1) + 1

            # تبديل الرموز لجعل البداية عادلة في كل جولة
            symbols = {}
            if round_count % 2 == 1:
                symbols[str(p_ids[0])] = "X"
                symbols[str(p_ids[1])] = "O"
                starter_index = 0
            else:
                symbols[str(p_ids[0])] = "O"
                symbols[str(p_ids[1])] = "X"
                starter_index = 1

            game_data['board'] = [""] * 9
            game_data['phase'] = 'playing'
            game_data['round_count'] = round_count
            game_data['turn_index'] = starter_index
            game_data['symbols'] = symbols
            game_data['winner_id'] = None

            cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
            conn.commit()

        return {"success": True}
    except Exception as e:
        print(f"Error resetting xo round: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()
