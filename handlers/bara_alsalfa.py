import random
import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import bot, ADMIN_ID

router = Router()

# كلمات اللعبة
CATEGORIES = {
    "فواكه": ["تفاح", "موز", "برتقال", "فراولة", "مانجو", "عنب"],
    "حيوانات": ["أسد", "فيل", "زرافة", "قطة", "كلب", "نمر"],
    "دول": ["السعودية", "مصر", "العراق", "الكويت", "الإمارات", "الأردن"],
    "أشياء في البيت": ["تلفاز", "ثلاجة", "سرير", "كرسي", "طاولة", "مكيف"]
}

# أوقات اللعبة الافتراضية
BARA_VOTE_TIME = 10
BARA_SPY_TIME = 15

class BaraState(StatesGroup):
    waiting_players = State()
    in_game = State()
    voting = State()
    spy_guessing = State()

@router.message(Command("bara"))
async def start_bara(message: types.Message, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ انضمام", callback_data="bara_join")
    builder.button(text="🎮 بدء اللعبة", callback_data="bara_start")
    builder.adjust(2)

    await message.answer(
        "🎮 **لعبة برا السالفة**\n\nاضغط على الزر للانضمام. نحتاج على الأقل 3 لاعبين.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(BaraState.waiting_players)
    await state.update_data(
        players=[message.from_user.id],
        player_names={message.from_user.id: message.from_user.full_name},
        creator_id=message.from_user.id
    )

@router.callback_query(F.data == "bara_join")
async def join_bara(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    players = data.get("players", [])
    names = data.get("player_names", {})

    if callback.from_user.id in players:
        await callback.answer("أنت منضم بالفعل!", show_alert=True)
        return

    players.append(callback.from_user.id)
    names[callback.from_user.id] = callback.from_user.full_name
    await state.update_data(players=players, player_names=names)

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ انضمام", callback_data="bara_join")
    builder.button(text="🎮 بدء اللعبة", callback_data="bara_start")
    builder.adjust(2)

    await callback.message.edit_text(
        f"🎮 **لعبة برا السالفة**\n\nاللاعبين المنضمين: {len(players)}\n" +
        "\n".join([f"- {n}" for n in names.values()]),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer("تم الانضمام!")

@router.callback_query(F.data == "bara_start")
async def start_game_logic(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    players = data.get("players", [])
    creator_id = data.get("creator_id")

    if callback.from_user.id != creator_id:
        await callback.answer("فقط منشئ اللعبة يمكنه البد~!", show_alert=True)
        return

    if len(players) < 3:
        await callback.answer("يجب توفر 3 لاعبين على الأقل!", show_alert=True)
        return

    category = random.choice(list(CATEGORIES.keys()))
    word = random.choice(CATEGORIES[category])
    out_player = random.choice(players)

    await state.update_data(out_player=out_player, word=word, category=category)
    await state.set_state(BaraState.in_game)

    for p_id in players:
        try:
            if p_id == out_player:
                await bot.send_message(p_id, f"🤫 أنت **برا السالفة**! حاول تموه وما تخليهم يعرفوك.\nالفئة هي: {category}")
            else:
                await bot.send_message(p_id, f"✅ السالفة هي: **{word}**\nالفئة: {category}\nحاولوا تعرفوا مين اللي برا السالفة!")
        except Exception:
            pass

    builder = InlineKeyboardBuilder()
    builder.button(text="🗳 ابدأ التصويت", callback_data="bara_start_voting")

    await callback.message.edit_text(
        f"تم اختيار السالفة! الفئة هي: **{category}**\nتحققوا من الخاص لمعرفة السالفة.\n\nتناقشوا الآن، وعندما تجهزون اضغطوا زر التصويت.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "bara_start_voting")
async def start_voting_callback(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    players = data.get("players", [])
    if callback.from_user.id not in players:
        await callback.answer("أنت لست في اللعبة!")
        return

    await state.set_state(BaraState.voting)
    await state.update_data(votes={})

    player_names = data.get("player_names", {})
    builder = InlineKeyboardBuilder()
    for p_id in players:
        builder.button(text=player_names[p_id], callback_data=f"bara_vote_{p_id}")
    builder.adjust(2)

    await callback.message.edit_text(
        f"🗳 **وقت التصويت!**\n\nأمامكم {BARA_VOTE_TIME} ثواني للتصويت.\nاللي ما يصوت النظام بيصوت عنه عشوائي!",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

    asyncio.create_task(vote_timeout_handler(callback.message, state))

async def vote_timeout_handler(message: types.Message, state: FSMContext):
    await asyncio.sleep(BARA_VOTE_TIME)
    if await state.get_state() != BaraState.voting:
        return

    data = await state.get_data()
    players, votes, player_names = data.get("players", []), data.get("votes", {}), data.get("player_names", {})
    out_player = data.get("out_player")

    # تصويت عشوائي لمن لم يصوت
    for p_id in players:
        if p_id not in votes:
            possible = [t for t in players if t != p_id]
            votes[p_id] = random.choice(possible)

    # حساب النتائج
    counts = {}
    for target in votes.values(): counts[target] = counts.get(target, 0) + 1
    voted_out_id = random.choice([pid for pid, c in counts.items() if c == max(counts.values())])
    voted_out_name = player_names[voted_out_id]

    await message.answer(f"📊 انتهى الوقت!\nتم التصويت ضد: **{voted_out_name}**", parse_mode="Markdown")

    if voted_out_id == out_player:
        await message.answer(f"🎯 كفو! **{voted_out_name}** هو اللي برا السالفة.\n\nيا {voted_out_name}، قدامك {BARA_SPY_TIME} ثانية تحزر السالفة وتفوز!")
        await start_spy_guess(message, state)
    else:
        spy_name = player_names[out_player]
        await message.answer(f"❌ خطأ! اللي كان برا السالفة هو **{spy_name}**.\nالسالفة كانت: **{data.get('word')}**\n\nفاز الجاسوس! 😎", parse_mode="Markdown")
        await state.clear()

@router.callback_query(F.data.startswith("bara_vote_"))
async def handle_vote(callback: types.CallbackQuery, state: FSMContext):
    if await state.get_state() != BaraState.voting:
        await callback.answer("انتهى وقت التصويت!")
        return

    data = await state.get_data()
    votes = data.get("votes", {})
    if callback.from_user.id in votes:
        await callback.answer("لقد صوّت بالفعل!")
        return

    target_id = int(callback.data.replace("bara_vote_", ""))
    votes[callback.from_user.id] = target_id
    await state.update_data(votes=votes)
    await callback.answer("تم تسجيل صوتك!")

async def start_spy_guess(message: types.Message, state: FSMContext):
    await state.set_state(BaraState.spy_guessing)
    data = await state.get_data()
    category = data.get("category")
    words = CATEGORIES.get(category, [])

    builder = InlineKeyboardBuilder()
    for word in words: builder.button(text=word, callback_data=f"bara_guess_{word}")
    builder.adjust(2)

    await message.answer(f"🤔 يا جاسوس، شنو هي السالفة؟ (الفئة: {category})", reply_markup=builder.as_markup())
    asyncio.create_task(spy_timeout_handler(message, state))

async def spy_timeout_handler(message: types.Message, state: FSMContext):
    await asyncio.sleep(BARA_SPY_TIME)
    if await state.get_state() != BaraState.spy_guessing: return

    data = await state.get_data()
    await message.answer(f"⌛ انتهى الوقت! الجاسوس ما حزر.\nالسالفة كانت: **{data.get('word')}**\n\nفاز اللاعبين! 🏆", parse_mode="Markdown")
    await state.clear()

@router.callback_query(F.data.startswith("bara_guess_"))
async def handle_guess(callback: types.CallbackQuery, state: FSMContext):
    if await state.get_state() != BaraState.spy_guessing: return
    data = await state.get_data()
    if callback.from_user.id != data.get("out_player"):
        await callback.answer("فقط الجاسوس يخمن!")
        return

    guessed = callback.data.replace("bara_guess_", "")
    actual = data.get("word")

    if guessed == actual:
        await callback.message.answer(f"🎉 كفو! الجاسوس حزرها صح: **{actual}**\n\nفاز الجاسوس! 😎", parse_mode="Markdown")
    else:
        await callback.message.answer(f"❌ خطأ! السالفة كانت: **{actual}**\n\nفاز اللاعبين! 🏆", parse_mode="Markdown")
    await state.clear()

@router.message(Command("bara_time"))
async def set_bara_time(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) != 3:
        await message.answer("الاستخدام: `/bara_time <vote/spy> <seconds>`")
        return

    global BARA_VOTE_TIME, BARA_SPY_TIME
    type_, sec = args[1].lower(), int(args[2])
    if type_ == "vote": BARA_VOTE_TIME = sec
    elif type_ == "spy": BARA_SPY_TIME = sec
    await message.answer(f"✅ تم تحديث وقت {type_} إلى {sec} ثانية.")
