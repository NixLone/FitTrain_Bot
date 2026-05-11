from aiogram.fsm.state import State, StatesGroup


class ProgressSG(StatesGroup):
    entering_weight = State()
    entering_comment = State()
