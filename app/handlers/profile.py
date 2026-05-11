from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.common import goal_kb
from app.keyboards.main_menu import get_main_menu
from app.services.users import get_user_by_tg_id, update_user_profile
from app.states.profile import ProfileSG

router = Router()


def _render_profile(user) -> str:
    lines = ["<b>Профиль</b>", ""]
    lines.append(f"Рост: <b>{user.height_cm or 'не указан'}</b>")
    lines.append(
        f"Вес: <b>{user.current_weight_kg if user.current_weight_kg is not None else 'не указан'}</b>"
    )
    lines.append(f"Цель на неделю: <b>{user.weekly_goal}</b> тренировок")
    lines.append("")
    lines.append("Чтобы обновить анкету, напиши /profile_setup")
    return "\n".join(lines)


@router.message(lambda m: m.text == "Профиль")
async def profile_menu(message: Message, session: AsyncSession) -> None:
    user = await get_user_by_tg_id(session, message.from_user.id)
    if not user:
        await message.answer("Сначала нажми /start", reply_markup=get_main_menu())
        return
    await message.answer(_render_profile(user), reply_markup=get_main_menu())


@router.message(Command("profile_setup"))
async def profile_setup_start(message: Message, state: FSMContext) -> None:
    await state.set_state(ProfileSG.entering_height)
    await message.answer("Укажи рост в сантиметрах. Например: 178")


@router.message(ProfileSG.entering_height)
async def profile_height(message: Message, state: FSMContext) -> None:
    try:
        height_cm = int(message.text.strip())
        if height_cm < 120 or height_cm > 240:
            raise ValueError
    except Exception:
        await message.answer("Введи рост числом в сантиметрах. Например: 178")
        return
    await state.update_data(height_cm=height_cm)
    await state.set_state(ProfileSG.entering_weight)
    await message.answer("Теперь укажи текущий вес в килограммах. Например: 82.5")


@router.message(ProfileSG.entering_weight)
async def profile_weight(message: Message, state: FSMContext) -> None:
    try:
        weight_kg = float(message.text.strip().replace(",", "."))
        if weight_kg < 30 or weight_kg > 300:
            raise ValueError
    except Exception:
        await message.answer("Введи вес числом. Например: 82.5")
        return
    await state.update_data(current_weight_kg=weight_kg)
    await state.set_state(ProfileSG.entering_goal)
    await message.answer(
        "Сколько тренировок в неделю планируешь?",
        reply_markup=goal_kb(),
    )


@router.message(ProfileSG.entering_goal)
async def profile_goal(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await get_user_by_tg_id(session, message.from_user.id)
    if not user:
        await state.clear()
        await message.answer("Сначала нажми /start", reply_markup=get_main_menu())
        return
    try:
        weekly_goal = int(message.text.strip())
        if weekly_goal < 1 or weekly_goal > 7:
            raise ValueError
    except Exception:
        await message.answer("Введи число от 1 до 7")
        return

    data = await state.get_data()
    await update_user_profile(
        session,
        user,
        height_cm=data["height_cm"],
        current_weight_kg=data["current_weight_kg"],
        weekly_goal=weekly_goal,
    )
    await state.clear()
    await message.answer(
        "Профиль обновил. Теперь можно сгенерировать план в разделе «План».",
        reply_markup=get_main_menu(),
    )
