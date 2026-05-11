from datetime import timedelta

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.common import duration_kb, skip_comment_kb, simple_choice_kb
from app.keyboards.main_menu import get_main_menu
from app.keyboards.reminders import (
    reminder_actions_kb,
    reminders_menu_kb,
    reschedule_kb,
    schedule_type_kb,
    skip_reason_kb,
)
from app.services.reminders import (
    complete_event,
    create_reminder,
    get_event,
    list_user_reminders,
    render_reminder_line,
    reschedule_event,
    skip_event,
)
from app.services.users import get_user_by_tg_id
from app.services.workout_types import list_available_workout_types
from app.states.reminders import CreateReminderSG, RescheduleSG
from app.states.workouts import CompleteEventSG
from app.utils.dt import (
    MOSCOW_TZ,
    format_moscow_dt,
    moscow_now,
    moscow_to_utc,
    parse_date_ddmmyyyy,
    parse_datetime_ddmmyyyy_hhmm,
    parse_time_hhmm,
    utc_now,
)

router = Router()


@router.message(lambda m: m.text == "Напоминания")
async def reminders_menu(message: Message) -> None:
    await message.answer("Управление напоминаниями:", reply_markup=reminders_menu_kb())


@router.callback_query(lambda c: c.data == "reminders:create")
async def reminders_create(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CreateReminderSG.choosing_schedule)
    await callback.message.answer("Выбери тип напоминания:", reply_markup=schedule_type_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "reminders:list")
async def reminders_list(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_user_by_tg_id(session, callback.from_user.id)
    if not user:
        await callback.message.answer("Сначала нажми /start")
        await callback.answer()
        return
    reminders = await list_user_reminders(session, user.id)
    if not reminders:
        await callback.message.answer("Активных напоминаний пока нет.")
    else:
        text = "<b>Твои напоминания</b>\n\n" + "\n".join(render_reminder_line(r) for r in reminders)
        await callback.message.answer(text)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("schedule:"))
async def choose_schedule(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    schedule_type = callback.data.split(":", 1)[1]
    await state.update_data(schedule_type=schedule_type)

    user = await get_user_by_tg_id(session, callback.from_user.id)
    if not user:
        await callback.message.answer("Сначала нажми /start")
        await callback.answer()
        return

    types_ = await list_available_workout_types(session, user.id)
    kb = simple_choice_kb([(item.name, f"rem_type:{item.id}") for item in types_], row_width=2)
    await state.set_state(CreateReminderSG.choosing_workout_type)
    await callback.message.answer("Выбери тип тренировки:", reply_markup=kb)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("rem_type:"))
async def choose_reminder_workout_type(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(workout_type_id=int(callback.data.split(":")[1]))
    await state.set_state(CreateReminderSG.entering_title)
    await callback.message.answer("Введи короткое название напоминания. Например: Вечерний зал")
    await callback.answer()


@router.message(CreateReminderSG.entering_title)
async def reminder_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(CreateReminderSG.entering_message)
    await message.answer("Теперь введи текст напоминания. Например: Пора заниматься 💪")


@router.message(CreateReminderSG.entering_message)
async def reminder_message(message: Message, state: FSMContext) -> None:
    await state.update_data(message_text=message.text.strip())
    data = await state.get_data()
    schedule_type = data["schedule_type"]
    if schedule_type == "weekly":
        await state.set_state(CreateReminderSG.entering_weekdays)
        await message.answer("Введи дни недели через запятую числами 1-7. Например: 1,3,5")
    elif schedule_type == "one_time":
        await state.set_state(CreateReminderSG.entering_date)
        await message.answer("Введи дату в формате ДД.ММ.ГГГГ. Например: 20.03.2026")
    else:
        await state.set_state(CreateReminderSG.entering_interval_days)
        await message.answer("Через сколько дней напоминать? Например: 2")


@router.message(CreateReminderSG.entering_weekdays)
async def reminder_weekdays(message: Message, state: FSMContext) -> None:
    try:
        weekdays = [int(x.strip()) for x in message.text.split(",") if x.strip()]
        if not weekdays or any(w not in range(1, 8) for w in weekdays):
            raise ValueError
    except Exception:
        await message.answer("Введи числа от 1 до 7 через запятую. Например: 1,3,5")
        return
    await state.update_data(weekdays=weekdays)
    await state.set_state(CreateReminderSG.entering_time)
    await message.answer("Введи время в формате ЧЧ:ММ. Например: 19:00")


@router.message(CreateReminderSG.entering_date)
async def reminder_one_time_date(message: Message, state: FSMContext) -> None:
    try:
        chosen_date = parse_date_ddmmyyyy(message.text)
    except Exception:
        await message.answer("Формат даты: 20.03.2026")
        return
    await state.update_data(date=str(chosen_date))
    await state.set_state(CreateReminderSG.entering_time)
    await message.answer("Введи время в формате ЧЧ:ММ. Например: 19:00")


@router.message(CreateReminderSG.entering_interval_days)
async def reminder_interval_days(message: Message, state: FSMContext) -> None:
    try:
        interval_days = int(message.text.strip())
        if interval_days <= 0:
            raise ValueError
    except Exception:
        await message.answer("Введи целое число дней. Например: 2")
        return
    await state.update_data(interval_days=interval_days)
    await state.set_state(CreateReminderSG.entering_time)
    await message.answer("Введи время в формате ЧЧ:ММ. Например: 19:00")


@router.message(CreateReminderSG.entering_time)
async def reminder_time(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        remind_time = parse_time_hhmm(message.text)
    except Exception:
        await message.answer("Формат времени: 19:00")
        return

    data = await state.get_data()
    user = await get_user_by_tg_id(session, message.from_user.id)
    if not user:
        await state.clear()
        await message.answer("Сначала нажми /start")
        return

    kwargs = {
        "session": session,
        "user_id": user.id,
        "workout_type_id": data["workout_type_id"],
        "title": data["title"],
        "message_text": data["message_text"],
        "schedule_type": data["schedule_type"],
        "remind_time": remind_time,
    }

    if data["schedule_type"] == "weekly":
        kwargs["weekdays"] = data["weekdays"]
    elif data["schedule_type"] == "one_time":
        from datetime import datetime
        date_val = parse_date_ddmmyyyy(data["date"][-10:].replace("-", ".")) if False else None
        # data['date'] хранится как ISO, поэтому собираем вручную
        y, m, d = map(int, data["date"].split("-"))
        local_dt = datetime(year=y, month=m, day=d, hour=remind_time.hour, minute=remind_time.minute, tzinfo=MOSCOW_TZ)
        kwargs["specific_date_local"] = local_dt
    else:
        kwargs["interval_days"] = data["interval_days"]

    reminder = await create_reminder(**kwargs)
    await state.clear()
    await message.answer(
        "Напоминание создано ✅\n"
        f"Следующий запуск: <b>{format_moscow_dt(reminder.next_run_at)}</b>",
        reply_markup=get_main_menu(),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("event:complete:"))
async def event_complete_start(callback: CallbackQuery, state: FSMContext) -> None:
    event_id = int(callback.data.split(":")[-1])
    await state.set_state(CompleteEventSG.entering_duration)
    await state.update_data(event_id=event_id)
    await callback.message.answer("Укажи длительность в минутах или нажми Пропустить", reply_markup=duration_kb())
    await callback.answer()


@router.message(CompleteEventSG.entering_duration)
async def event_complete_duration(message: Message, state: FSMContext) -> None:
    value = None
    if message.text != "Пропустить":
        try:
            value = int(message.text)
        except Exception:
            await message.answer("Введи число минут или нажми Пропустить")
            return
    await state.update_data(duration=value)
    await state.set_state(CompleteEventSG.entering_comment)
    await message.answer("Добавь комментарий или нажми 'Пропустить комментарий'", reply_markup=skip_comment_kb())


@router.message(CompleteEventSG.entering_comment)
async def event_complete_comment(message: Message, state: FSMContext) -> None:
    comment = None if message.text == "Пропустить комментарий" else message.text.strip()
    await state.update_data(comment=comment)
    await state.set_state(CompleteEventSG.entering_datetime)
    await message.answer("Когда была тренировка? Напиши 'сейчас' или дату в формате 17.03.2026 19:30", reply_markup=get_main_menu())


@router.message(CompleteEventSG.entering_datetime)
async def event_complete_finish(message: Message, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    event = await get_event(session, data["event_id"])
    if not event:
        await state.clear()
        await message.answer("Событие не найдено", reply_markup=get_main_menu())
        return

    text = message.text.strip().lower()
    if text == "сейчас":
        performed_at = utc_now()
    else:
        try:
            performed_at = moscow_to_utc(parse_datetime_ddmmyyyy_hhmm(message.text))
        except Exception:
            await message.answer("Формат: 17.03.2026 19:30 или 'сейчас'")
            return

    await complete_event(
        session,
        event=event,
        performed_at=performed_at,
        duration_minutes=data.get("duration"),
        comment=data.get("comment"),
    )
    await state.clear()
    await message.answer("Отлично, тренировку записал ✅", reply_markup=get_main_menu())


@router.callback_query(lambda c: c.data and c.data.startswith("event:skip:"))
async def event_skip_start(callback: CallbackQuery) -> None:
    event_id = int(callback.data.split(":")[-1])
    await callback.message.answer("Почему пропуск?", reply_markup=skip_reason_kb(event_id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("skip_reason:"))
async def event_skip_reason(callback: CallbackQuery, session: AsyncSession) -> None:
    _, event_id, reason = callback.data.split(":", 2)
    event = await get_event(session, int(event_id))
    if not event:
        await callback.answer("Событие не найдено", show_alert=True)
        return
    await skip_event(session, event=event, reason=reason)
    await callback.message.answer("Записал пропуск. Ничего страшного, идём дальше.", reply_markup=get_main_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("event:reschedule:"))
async def event_reschedule_start(callback: CallbackQuery) -> None:
    event_id = int(callback.data.split(":")[-1])
    await callback.message.answer("Куда перенести?", reply_markup=reschedule_kb(event_id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("resch:"))
async def event_reschedule_choice(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    _, event_id, option = callback.data.split(":", 2)
    event = await get_event(session, int(event_id))
    if not event:
        await callback.answer("Событие не найдено", show_alert=True)
        return

    now_local = moscow_now()
    new_dt = None
    if option == "30m":
        new_dt = now_local + timedelta(minutes=30)
    elif option == "today21":
        new_dt = now_local.replace(hour=21, minute=0, second=0, microsecond=0)
    elif option == "tomorrow9":
        base = now_local + timedelta(days=1)
        new_dt = base.replace(hour=9, minute=0, second=0, microsecond=0)
    elif option == "tomorrow19":
        base = now_local + timedelta(days=1)
        new_dt = base.replace(hour=19, minute=0, second=0, microsecond=0)
    elif option == "custom":
        await state.set_state(RescheduleSG.entering_custom_datetime)
        await state.update_data(event_id=int(event_id))
        await callback.message.answer("Введи дату и время в формате 17.03.2026 19:30")
        await callback.answer()
        return

    await reschedule_event(session, event=event, new_dt_local=new_dt)
    await callback.message.answer(f"Перенёс. Новое время: <b>{new_dt.strftime('%d.%m.%Y %H:%M')}</b>", reply_markup=get_main_menu())
    await callback.answer()


@router.message(RescheduleSG.entering_custom_datetime)
async def event_reschedule_custom(message: Message, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    event = await get_event(session, data["event_id"])
    if not event:
        await state.clear()
        await message.answer("Событие не найдено", reply_markup=get_main_menu())
        return
    try:
        local_dt = parse_datetime_ddmmyyyy_hhmm(message.text)
    except Exception:
        await message.answer("Формат: 17.03.2026 19:30")
        return
    await reschedule_event(session, event=event, new_dt_local=local_dt)
    await state.clear()
    await message.answer(f"Перенёс на <b>{message.text}</b>", reply_markup=get_main_menu())
