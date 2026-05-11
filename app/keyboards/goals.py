from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def goal_picker_kb(current_goal: int | None = None) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for goal in range(1, 8):
        marker = "✓ " if current_goal == goal else ""
        row.append(
            InlineKeyboardButton(
                text=f"{marker}{goal}",
                callback_data=f"goal:set:{goal}",
            )
        )
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)
