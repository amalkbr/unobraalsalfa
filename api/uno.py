import random
import string
import json
from fastapi import APIRouter
from .database import get_db_conn, RealDictCursor
from collections import Counter

router = APIRouter()

UNO_DECK_TOTAL = 110

def generate_deck():
    colors = ['🔴', '🔵', '🟡', '🟢']
    deck = []
    for c in colors:
        deck.append(f"{c} 0")
        for n in range(1, 10): deck.extend([f"{c} {n}"] * 2)
        deck.extend([f"{c} 🚫", f"{c} 🔄", f"{c} ⬆️2"] * 2)
    deck.extend(["🌈 جوكر"] * 4)
    deck.extend(["🔥 جوكر+4"] * 4)
    deck.append("💧 جوكر+1")
    deck.append("🌊 جوكر+2")
    random.shuffle(deck)
    return deck

def check_validity(card, top_card, current_color):
    if any(x in card for x in ["🌈", "🔥", "💧", "🌊"]):
        return True
    parts = card.split()
    if len(parts) < 2: return False
    c_color, c_value = parts[0], parts[1]
    if c_color == current_color: return True
    top_parts = top_card.split()
    top_value = top_parts[1] if len(top_parts) > 1 else top_parts[0]
    if c_value == top_value: return True
    return False

def calculate_points(hand):
    total = 0
    for card in hand:
        if any(x in card for x in ["🌈", "🔥", "💧", "🌊"]): total += 50
        elif any(x in card for x in ["🚫", "🔄", "⬆️2"]): total += 20
        else:
            try: total += int(card.split()[-1])
            except: total += 10
    return total

def sort_hand(hand):
    card_counts = Counter(card.split()[0] for card in hand if card.split()[0] in ['🔴', '🔵', '🟡', '🟢'])
    def card_sort_key(card):
        parts = card.split()
        color = parts[0]
        if any(x in card for x in ["🌈", "🔥", "💧", "🌊"]): return (3, 0, card)
        if color in ['🔴', '🔵', '🟡', '🟢']:
            count = card_counts.get(color, 0)
            return (0, -count, color, card) if count > 1 else (1, color, card)
        return (2, card)
    hand.sort(key=card_sort_key)
    return hand

def ensure_deck_from_discard(game_data):
    deck = game_data.get('deck', [])
    if deck: return deck
    discard = game_data.get('discard_pile', [])
    if not discard: return []
    new_deck = list(discard)
    random.shuffle(new_deck)
    game_data['deck'] = new_deck
    game_data['discard_pile'] = []
    return new_deck

@router.post("/api/uno/create")
async def create_uno_room_endpoint(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection error"}
    try:
        user_id = int(data['user_id'])
        player_name = data['player_name']
        max_players = int(data.get('max_players', 4))
        room_code = ''.join(random.choices(string.ascii_uppercase, k=4))

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO rooms (room_code, room_id, host_id, creator_id, status, game_type, win_limit, max_players)
                VALUES (%s, %s, %s, %s, 'lobby', 'uno', 100, %s)
            """, (room_code, room_code, user_id, user_id, max_players))

            cur.execute("""
                INSERT INTO room_players (room_code, room_id, user_id, player_name, join_order, said_uno)
                VALUES (%s, %s, %s, %s, 0, FALSE)
            """, (room_code, room_code, user_id, player_name))

            conn.commit()
        return {"success": True, "room_code": room_code}
    except Exception as e:
        print(f"Error creating uno room: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@router.post("/api/uno/start")
async def start_uno_game_endpoint(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection error"}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT host_id, game_type FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room or room['game_type'] != 'uno':
                return {"success": False, "msg": "الغرفة غير موجودة"}
            if room['host_id'] != user_id:
                return {"success": False, "msg": "المضيف فقط يمكنه بدء اللعبة"}

            cur.execute("SELECT user_id, player_name FROM room_players WHERE room_code = %s ORDER BY join_order", (room_code,))
            players = cur.fetchall()
            n = len(players)

            if n < 2:
                return {"success": False, "msg": "يجب أن يكون عدد اللاعبين 2 على الأقل"}

            p_ids = [p['user_id'] for p in players]

            # Generate deck and distribute 7 cards to each player
            all_cards = generate_deck()
            hands = {}
            for pid in p_ids:
                hands[str(pid)] = sort_hand([all_cards.pop() for _ in range(7)])

            # Choose first card (must not be a special wild card to make starting easy)
            first_card = all_cards.pop()
            while any(x in first_card for x in ["🌈", "🔥", "💧", "🌊"]):
                all_cards.insert(0, first_card) # return back
                random.shuffle(all_cards)
                first_card = all_cards.pop()

            # Set starting color
            start_color = first_card.split()[0] if first_card.split() else '🔴'

            game_data = {
                "hands": hands,
                "deck": all_cards,
                "discard_pile": [first_card],
                "top_card": first_card,
                "current_color": start_color,
                "turn_index": 0,
                "direction": 1, # 1 for clockwise, -1 for counter-clockwise
                "ordered_ids": p_ids,
                "phase": "playing",
                "round_count": 1,
                "winner_id": None
            }

            cur.execute("UPDATE rooms SET status = 'playing', game_data = %s WHERE room_code = %s",
                        (json.dumps(game_data), room_code))
            cur.execute("UPDATE room_players SET said_uno = FALSE WHERE room_code = %s", (room_code,))
            conn.commit()

        return {"success": True}
    except Exception as e:
        print(f"Error starting uno: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@router.post("/api/uno/play")
async def uno_play_card(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection error"}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])
        card = data['card'] # e.g. "🔴 5" or "🌈 جوكر"
        chosen_color = data.get('chosen_color', '🔴') # for wild cards

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT game_data, status FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room or room['status'] != 'playing':
                return {"success": False, "msg": "اللعبة ليست مستمرة"}

            game_data = json.loads(room['game_data'])
            ordered_ids = game_data['ordered_ids']
            turn_idx = game_data['turn_index']

            if ordered_ids[turn_idx] != user_id:
                return {"success": False, "msg": "ليس دورك الآن"}

            hand = game_data['hands'].get(str(user_id), [])
            if card not in hand:
                return {"success": False, "msg": "الورقة ليست في يدك"}

            top_card = game_data['top_card']
            current_color = game_data['current_color']

            if not check_validity(card, top_card, current_color):
                return {"success": False, "msg": "لا يمكنك لعب هذه الورقة"}

            # Remove card from hand
            hand.remove(card)
            game_data['hands'][str(user_id)] = sort_hand(hand)

            # Update discard pile and top card
            game_data['discard_pile'].append(card)
            game_data['top_card'] = card

            # Reset said_uno for other players if they no longer have 1 card
            cur.execute("UPDATE room_players SET said_uno = FALSE WHERE room_code = %s AND user_id != %s", (room_code, user_id))

            # Apply card effects
            next_turn_idx = turn_idx
            direction = game_data.get('direction', 1)
            players_count = len(ordered_ids)

            # Check if this card changes the color (wild cards)
            is_wild = any(x in card for x in ["🌈", "🔥", "💧", "🌊"])
            if is_wild:
                game_data['current_color'] = chosen_color
            else:
                game_data['current_color'] = card.split()[0]

            # Check special card actions
            skip_next = False
            draw_count = 0

            if "🚫" in card: # Skip
                skip_next = True
            elif "🔄" in card: # Reverse
                if players_count == 2:
                    skip_next = True # acts as skip in 2 players
                else:
                    direction = -direction
                    game_data['direction'] = direction
            elif "⬆️2" in card: # Draw 2
                draw_count = 2
                skip_next = True
            elif "🔥" in card: # Wild Draw 4
                draw_count = 4
                skip_next = True
            elif "💧" in card: # Wild Draw 1
                draw_count = 1
                skip_next = True
            elif "🌊" in card: # Wild Draw 2
                draw_count = 2
                skip_next = True

            # If next player needs to draw cards
            if draw_count > 0:
                next_p_idx = (turn_idx + direction) % players_count
                next_p_id = ordered_ids[next_p_idx]
                next_p_hand = game_data['hands'].get(str(next_p_id), [])
                
                # Draw cards
                deck = ensure_deck_from_discard(game_data)
                for _ in range(draw_count):
                    if deck:
                        next_p_hand.append(deck.pop())
                game_data['hands'][str(next_p_id)] = sort_hand(next_p_hand)
                # Reset uno safety for victim
                cur.execute("UPDATE room_players SET said_uno = FALSE WHERE room_code = %s AND user_id = %s", (room_code, next_p_id))

            # Check for round winner
            if len(hand) == 0:
                # Player won! Calculate total points
                round_score = 0
                for pid in ordered_ids:
                    if pid != user_id:
                        p_hand = game_data['hands'].get(str(pid), [])
                        round_score += calculate_points(p_hand)
                
                # Add score to database for winner
                cur.execute("UPDATE room_players SET score = score + %s WHERE room_code = %s AND user_id = %s", (room_code, user_id))
                
                game_data['phase'] = 'finished'
                game_data['winner_id'] = user_id
                
                cur.execute("UPDATE rooms SET status = 'finished', game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                conn.commit()
                return {"success": True, "msg": f"لقد فزت بالجولة وحصلت على {round_score} نقطة!"}

            # Update turn index
            step = 2 if skip_next else 1
            next_turn_idx = (turn_idx + (direction * step)) % players_count
            game_data['turn_index'] = next_turn_idx

            cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
            conn.commit()

        return {"success": True}
    except Exception as e:
        print(f"Error playing card: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@router.post("/api/uno/draw")
async def uno_draw_card(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection error"}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT game_data, status FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room or room['status'] != 'playing':
                return {"success": False, "msg": "اللعبة ليست مستمرة"}

            game_data = json.loads(room['game_data'])
            ordered_ids = game_data['ordered_ids']
            turn_idx = game_data['turn_index']

            if ordered_ids[turn_idx] != user_id:
                return {"success": False, "msg": "ليس دورك الآن"}

            # Draw card
            deck = ensure_deck_from_discard(game_data)
            if not deck:
                return {"success": False, "msg": "رزمة السحب فارغة تماماً!"}

            card = deck.pop()
            hand = game_data['hands'].get(str(user_id), [])
            hand.append(card)
            game_data['hands'][str(user_id)] = sort_hand(hand)

            # Player drew, so they are not safe from Uno catch
            cur.execute("UPDATE room_players SET said_uno = FALSE WHERE room_code = %s AND user_id = %s", (room_code, user_id))

            # Check if drawn card is playable
            top_card = game_data['top_card']
            current_color = game_data['current_color']
            is_playable = check_validity(card, top_card, current_color)

            # If not playable, we pass the turn automatically
            if not is_playable:
                direction = game_data.get('direction', 1)
                players_count = len(ordered_ids)
                next_turn_idx = (turn_idx + direction) % players_count
                game_data['turn_index'] = next_turn_idx
                msg = f"سحبت {card} وتم تمرير الدور لعدم إمكانية اللعب."
            else:
                msg = f"سحبت {card} ويمكنك لعبها الآن أو التمرير."

            cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
            conn.commit()

        return {"success": True, "card": card, "is_playable": is_playable, "msg": msg}
    except Exception as e:
        print(f"Error drawing card: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@router.post("/api/uno/pass")
async def uno_pass_turn(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection error"}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT game_data, status FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room or room['status'] != 'playing':
                return {"success": False, "msg": "اللعبة ليست مستمرة"}

            game_data = json.loads(room['game_data'])
            ordered_ids = game_data['ordered_ids']
            turn_idx = game_data['turn_index']

            if ordered_ids[turn_idx] != user_id:
                return {"success": False, "msg": "ليس دورك الآن"}

            # Pass turn to next player
            direction = game_data.get('direction', 1)
            players_count = len(ordered_ids)
            next_turn_idx = (turn_idx + direction) % players_count
            game_data['turn_index'] = next_turn_idx

            cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
            conn.commit()

        return {"success": True}
    except Exception as e:
        print(f"Error passing turn: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@router.post("/api/uno/say_uno")
async def uno_say_uno_endpoint(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection error"}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id'])

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT game_data, status FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room or room['status'] != 'playing':
                return {"success": False, "msg": "اللعبة ليست مستمرة"}

            game_data = json.loads(room['game_data'])
            hand = game_data['hands'].get(str(user_id), [])

            # Can only say uno if has 1 or 2 cards in hand (safety check)
            if len(hand) > 2:
                return {"success": False, "msg": "لا يمكنك صياح أونو إلا إذا كان لديك ورقتين أو ورقة واحدة فقط!"}

            cur.execute("UPDATE room_players SET said_uno = TRUE WHERE room_code = %s AND user_id = %s", (room_code, user_id))
            conn.commit()

        return {"success": True}
    except Exception as e:
        print(f"Error saying uno: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()

@router.post("/api/uno/catch")
async def uno_catch_endpoint(data: dict):
    conn = get_db_conn()
    if not conn: return {"success": False, "msg": "Database connection error"}
    try:
        room_code = data['room_code'].upper()
        user_id = int(data['user_id']) # the catcher
        target_id = int(data['target_id']) # the victim who forgot Uno

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT game_data, status FROM rooms WHERE room_code = %s", (room_code,))
            room = cur.fetchone()
            if not room or room['status'] != 'playing':
                return {"success": False, "msg": "اللعبة ليست مستمرة"}

            cur.execute("SELECT said_uno, player_name FROM room_players WHERE room_code = %s AND user_id = %s", (room_code, target_id))
            target_player = cur.fetchone()
            if not target_player:
                return {"success": False, "msg": "اللاعب المستهدف غير موجود"}

            game_data = json.loads(room['game_data'])
            target_hand = game_data['hands'].get(str(target_id), [])

            # Target must have exactly 1 card and has NOT said uno
            if len(target_hand) == 1 and not target_player['said_uno']:
                # Draw 2 penalty cards for victim
                deck = ensure_deck_from_discard(game_data)
                for _ in range(2):
                    if deck:
                        target_hand.append(deck.pop())
                game_data['hands'][str(target_id)] = sort_hand(target_hand)
                
                cur.execute("UPDATE rooms SET game_data = %s WHERE room_code = %s", (json.dumps(game_data), room_code))
                cur.execute("UPDATE room_players SET said_uno = FALSE WHERE room_code = %s AND user_id = %s", (room_code, target_id))
                conn.commit()
                return {"success": True, "msg": f"🪤 لقد صدت {target_player['player_name']}! تم عقابه بسحب ورقتين."}
            else:
                return {"success": False, "msg": "اللاعب في أمان أو لا تنطبق عليه شروط الصيد!"}
    except Exception as e:
        print(f"Error catching player: {e}")
        return {"success": False, "msg": str(e)}
    finally: conn.close()
