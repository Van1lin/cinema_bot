from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# головне меню
def main_menu():
    b = ReplyKeyboardBuilder()
    b.button(text="🎬 /films")
    b.button(text="🔎 /search")
    b.button(text="🎭 /genres")
    b.button(text="🎲 /random")
    b.button(text="⭐ /favorites")
    b.adjust(2)
    return b.as_markup(resize_keyboard=True)

# список фільмів
def films_keyboard(films, prefix="movie_"):
    b = InlineKeyboardBuilder()
    for f in films:
        b.button(text=f"🎬 {f['title']}", callback_data=f"{prefix}{f['id']}")
    b.adjust(1)
    return b

# список жанрів
def genres_keyboard(genres):
    b = InlineKeyboardBuilder()
    for g in genres:
        # Используем латинские символы в callback_data
        b.button(text=f"🎭 {g}", callback_data=f"genre_{g.replace(' ', '_')}")
    b.adjust(2)
    return b

# дії з конкретним фільмом
def film_actions(id, admin: bool = False):
    b = InlineKeyboardBuilder()
    b.button(text="⭐ Оцінити", callback_data=f"rate_{id}")
    b.button(text="❤️ В улюблені", callback_data=f"fav_{id}")
    if admin:
        b.button(text="✏️ Редагувати", callback_data=f"edit_{id}")
    b.adjust(2)
    return b

# клавіатура для виставлення рейтингу
def rating_keyboard(id):
    b = InlineKeyboardBuilder()
    for i in range(1, 11):
        b.button(text=str(i), callback_data=f"rate_{id}_{i}")
    b.adjust(5)
    return b

# підтвердження дії (наприклад видалення)
def confirm_keyboard(id):
    b = InlineKeyboardBuilder()
    b.button(text="✅ Так", callback_data=f"confirm_{id}")
    b.button(text="❌ Ні", callback_data="cancel")
    b.adjust(2)
    return b

# меню редагування полів фільму
def edit_keyboard(id):
    b = InlineKeyboardBuilder()
    b.button(text="🎬 Назва", callback_data=f"editfield_{id}_title")
    b.button(text="🎭 Жанр", callback_data=f"editfield_{id}_genre")
    b.button(text="📝 Опис", callback_data=f"editfield_{id}_description")
    b.button(text="👤 Актори", callback_data=f"editfield_{id}_actors")
    b.button(text="🖼 Постер", callback_data=f"editfield_{id}_poster")
    b.adjust(2)
    return b