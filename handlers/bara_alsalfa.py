import random
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

# كلمات اللعبة (أمثلة ويمكن توسيعها)
CATEGORIES = {
    "فواكه": ["تفاح", "موز", "برتقال", "فراولة", "مانجو", "عنب"],
    "حيوانات": ["أسد", "فيل", "زرافة", "قطة", "كلب", "نمر"],
    "دول": ["السعودية", "مصر", "العراق", "الكويت", "الإمارات", "الأردن"],
    "أشياء في البيت": ["تلفاز", "ثلاجة", "سرير", "كرسي", "طاولة", "مكيف"]
}

class BaraState(StatesGroup):
    waiting_players = State()
    in_game = State()

@router.message(Command("bara"))
async def start_bara(message: types.Message, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text="انضمام للعبة", callback_data="bara_join")
    builder.button(text="بدء اللعبة", callback_data="bara_start")

    await message.answer(
        "🎮 **لعبة برا السالفة**\n\nاضغط على الزر للانضمام. نحتاج على الأقل 3 لاعبين.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(BaraState.waiting_players)
    await state.update_data(players=[message.from_user.id], player_names={message.from_user.id: message.from_user.full_name})

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

    await callback.message.edit_text(
        f"🎮 **لعبة برا السالفة**\n\nاللاعبين المنضمين: {len(players)}\n" +
        "\n".join([f"- {n}" for n in names.values()]),
        reply_markup=callback.message.reply_markup,
        parse_mode="Markdown"
    )
    await callback.answer("تم الانضمام!")

@router.callback_query(F.data == "bara_start")
async def start_game_logic(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    players = data.get("players", [])

    if len(players) < 3:
        await callback.answer("يجب توفر 3 لاعبين على الأقل!", show_alert=True)
        return

    # اختيار السالفة
    category = random.choice(list(CATEGORIES.keys()))
    word = random.choice(CATEGORIES[category])

    # اختيار الشخص اللي "برا السالفة"
    out_player = random.choice(players)

    await state.update_data(out_player=out_player, word=word, category=category)
    await state.set_state(BaraState.in_game)

    await callback.message.edit_text(f"تم اختيار السالفة! الفئة هي: **{category}**\nتحققوا من الخاص لمعرفة السالفة.", parse_mode="Markdown")

    from config import bot
    for p_id in players:
        if p_id == out_player:
            await bot.send_message(p_id, f"🤫 أنت **برا السالفة**! حاول تموه وما تخليهم يعرفوك. الفئة هي: {category}")
        else:
            await bot.send_message(p_id, f"✅ السالفة هي: **{word}**\nالفئة: {category}\nحاولوا تعرفوا مين اللي برا السالفة!")
