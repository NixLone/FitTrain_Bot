from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.dt import WEEKDAY_MAP


def plan_actions_kb(has_plan: bool) -> InlineKeyboardMarkup:
    label = "Изменить план" if has_plan else "Собрать план"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data="plan:wizard:start")],
        ]
    )


def weekday_picker_kb(selected_days: set[int]) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for day in range(1, 8):
        marker = "✓ " if day in selected_days else ""
        row.append(
            InlineKeyboardButton(
                text=f"{marker}{WEEKDAY_MAP[day]}",
                callback_data=f"plan:day:{day}",
            )
        )
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="Готово", callback_data="plan:days:done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def duration_picker_kb(selected_minutes: int | None) -> InlineKeyboardMarkup:
    options = [30, 45, 60, 75, 90, 120]
    rows = []
    row = []
    for minutes in options:
        marker = "✓ " if selected_minutes == minutes else ""
        row.append(
            InlineKeyboardButton(
                text=f"{marker}{minutes} мин",
                callback_data=f"plan:duration:{minutes}",
            )
        )
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="Готово", callback_data="plan:duration:done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def workout_type_picker_kb(options: list[tuple[int, str]], selected_ids: set[int]) -> InlineKeyboardMarkup:
    rows = []
    for type_id, name in options:
        marker = "✓ " if type_id in selected_ids else ""
        rows.append(
            [InlineKeyboardButton(text=f"{marker}{name}", callback_data=f"plan:type:{type_id}")]
        )
    rows.append([InlineKeyboardButton(text="Готово", callback_data="plan:types:done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
