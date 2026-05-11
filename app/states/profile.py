from aiogram.fsm.state import State, StatesGroup


class ProfileSG(StatesGroup):
    entering_height = State()
    entering_weight = State()
    entering_goal = State()
