# Стан для додавання та редагування фільму

from aiogram.fsm.state import StatesGroup, State

class AddFilm(StatesGroup):
    title = State()
    genre = State()
    description = State()
    actors = State()
    poster = State()

class EditFilm(StatesGroup):
    field = State()       
    new_value = State()