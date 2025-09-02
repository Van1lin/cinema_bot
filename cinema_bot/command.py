# Обробники команд та логіка 🎬

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from config import ADMIN_ID
from data import Database
from keyboards import (
    main_menu,
    films_keyboard,
    genres_keyboard,
    film_actions,
    rating_keyboard,
    confirm_keyboard,
    edit_keyboard,
)
from models import AddFilm, EditFilm

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

router = Router()
db = Database()

# Перевірка чи користувач адмін
def is_admin(uid: int) -> bool:
    try:
        return int(uid) in [int(admin_id) for admin_id in ADMIN_ID]
    except Exception:
        return False

# Показ картки з інформацією про фільм
async def show_card(message, film: dict) -> None:
    text = (
        f"🎬 <b>{film.get('title', 'Без назви')}</b>\n\n"
        f"🎭 <b>Жанр:</b> {film.get('genre', 'не вказано')}\n"
        f"⭐ <b>Рейтинг:</b> {film.get('rating', 0):.2f} / 10 ({film.get('votes', 0)} голосів)\n\n"
        f"📖 <b>Опис:</b>\n<i>{film.get('description', 'немає опису')}</i>\n\n"
        f"👥 <b>Актори:</b> {film.get('actors', 'не вказано')}"
    )
    user_id = getattr(message.from_user, "id", None)
    admin = is_admin(user_id) if user_id else False
    kb = film_actions(film['id'], admin=admin)  # ВСЕГДА показуємо кнопку редагування адмінам
    poster = film.get('poster') or ""
    if poster.startswith(("http://", "https://")):
        try:
            await message.answer_photo(photo=poster, caption=text, reply_markup=kb.as_markup())
            return
        except Exception:
            pass
    await message.answer(text, reply_markup=kb.as_markup())

# --- Основні команди ---

@router.message(Command("start", "help"))
async def cmd_start(message: Message):
    await message.answer(
        "🎭 <b>Кіноафіша</b>\n\n"
        "Команди:\n"
        "/films - всі фільми\n"
        "/search - пошук\n"
        "/genres - фільми за жанром\n"
        "/random - випадкова рекомендація\n"
        "/favorites - мої улюблені\n"
        "/add - додати фільм (тільки адмін)\n"
        "/delete - видалити фільм (тільки адмін)",
        reply_markup=main_menu()
    )

@router.message(Command("films"))
async def cmd_films(message: Message):
    films = db.get_films()
    if not films:
        await message.answer("📭 Бібліотека порожня. Адмін може додати фільм командою /add")
        return
    
    user_id = message.from_user.id
    admin = is_admin(user_id)
    
    kb = films_keyboard(films)
    await message.answer("🎥 Усі фільми:", reply_markup=kb.as_markup())
    
    if admin:
        await message.answer("⚙️ Як адмін, ви можете редагувати фільми, натиснувши на них")

@router.message(Command("genres"))
async def cmd_genres(message: Message):
    films = db.get_films()
    if not films:
        await message.answer("📭 Немає фільмів для фільтрації")
        return
    genres = sorted({(m.get("genre") or "").strip() for m in films if m.get("genre")})
    if not genres:
        await message.answer("📭 Жанри не вказані")
        return
    kb = genres_keyboard(genres)
    await message.answer("🎭 Оберіть жанр:", reply_markup=kb.as_markup())

@router.message(Command("random"))
async def cmd_random(message: Message):
    f = db.random_film()
    if not f:
        await message.answer("Поки що немає фільмів для рекомендації")
        return
    await show_card(message, f)

@router.message(Command("favorites"))
async def cmd_favorites(message: Message):
    favs = db.get_favorites(message.from_user.id)
    if not favs:
        await message.answer("❤️ У вас поки що немає улюблених фільмів")
        return
    
    user_id = message.from_user.id
    admin = is_admin(user_id)
    
    kb = films_keyboard(favs, prefix="movie_")
    await message.answer("❤️ Ваші улюблені:", reply_markup=kb.as_markup())
    
    if admin:
        await message.answer("⚙️ Як адмін, ви можете редагувати фільми, натиснувши на них")

@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    await state.set_state("waiting_for_search")
    await message.answer("🔍 Введіть назву фільму для пошуку")

@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Тільки адмін може додавати фільми")
        return
    await state.set_state(AddFilm.title)
    await message.answer("📝 Введіть назву фільму")

@router.message(Command("delete"))
async def cmd_delete(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Тільки адмін може видаляти фільми")
        return
    films = db.get_films()
    if not films:
        await message.answer("Немає фільмів для видалення")
        return
    kb = films_keyboard(films, prefix="delete_")
    await message.answer("🗑️ Оберіть фільм для видалення:", reply_markup=kb.as_markup())

# --- ОБРОБНИКИ КНОПОК З ЕМОДЗИ ---

@router.message(F.text == "🎬 /films")
async def handle_films_button(message: Message):
    await cmd_films(message)

@router.message(F.text == "🔎 /search")
async def handle_search_button(message: Message, state: FSMContext):
    await cmd_search(message, state)

@router.message(F.text == "🎭 /genres")
async def handle_genres_button(message: Message):
    await cmd_genres(message)

@router.message(F.text == "🎲 /random")
async def handle_random_button(message: Message):
    await cmd_random(message)

@router.message(F.text == "⭐ /favorites")
async def handle_favorites_button(message: Message):
    await cmd_favorites(message)

# --- ОБРОБНИКИ CALLBACK ---

@router.callback_query(F.data.startswith("movie_"))
async def show_film_callback(callback: CallbackQuery):
    film_id = int(callback.data.split("_")[1])
    film = db.get_film_by_id(film_id)
    if not film:
        await callback.message.answer("❌ Фільм не знайдено")
        await callback.answer()
        return
    
    await show_card(callback.message, film)
    await callback.answer()

@router.callback_query(F.data.startswith("genre_"))
async def show_genre_films(callback: CallbackQuery):
    genre_encoded = callback.data.split("_", 1)[1]
    genre = genre_encoded.replace('_', ' ')
    films = db.filter_by_genre(genre)
    if not films:
        await callback.message.answer(f"❌ Немає фільмів у жанрі '{genre}'")
        await callback.answer()
        return
    
    user_id = callback.from_user.id
    admin = is_admin(user_id)
    
    kb = films_keyboard(films)
    await callback.message.answer(f"🎭 Фільми у жанрі '{genre}':", reply_markup=kb.as_markup())
    
    if admin:
        await callback.message.answer("⚙️ Як адмін, ви можете редагувати фільми, натиснувши на них")
    
    await callback.answer()

@router.callback_query(F.data.startswith("fav_"))
async def toggle_favorite(callback: CallbackQuery):
    film_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    added = db.toggle_favorite(film_id, user_id)
    action = "додано до" if added else "видалено з"
    await callback.answer(f"❤️ Фільм {action} улюблених")

@router.callback_query(F.data.startswith("rate_"))
async def rate_film(callback: CallbackQuery):
    parts = callback.data.split("_")
    if len(parts) == 2:
        # Показ клавіатури з рейтингом
        film_id = int(parts[1])
        kb = rating_keyboard(film_id)
        await callback.message.answer("⭐ Оберіть рейтинг (1-10):", reply_markup=kb.as_markup())
    elif len(parts) == 3:
        # Обробка вибору рейтингу
        film_id = int(parts[1])
        rating = int(parts[2])
        user_id = callback.from_user.id
        avg_rating = db.add_rating(film_id, user_id, rating)
        await callback.message.answer(f"⭐ Ваш рейтинг {rating}/10 додано! Середній рейтинг: {avg_rating:.2f}")
    await callback.answer()

# --- FSM процеси додавання ---

@router.message(StateFilter(AddFilm.title))
async def process_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()
    if not title:
        await message.answer("Назва не може бути порожньою")
        return
    await state.update_data(title=title)
    await state.set_state(AddFilm.genre)
    await message.answer("🎭 Вкажіть жанр")

@router.message(StateFilter(AddFilm.genre))
async def process_genre(message: Message, state: FSMContext):
    genre = (message.text or "").strip()
    if not genre:
        await message.answer("Жанр не може бути порожнім")
        return
    await state.update_data(genre=genre)
    await state.set_state(AddFilm.description)
    await message.answer("📝 Введіть опис фільму")

@router.message(StateFilter(AddFilm.description))
async def process_description(message: Message, state: FSMContext):
    description = (message.text or "").strip()
    await state.update_data(description=description)
    await state.set_state(AddFilm.actors)
    await message.answer("👥 Введіть акторів (через кому)")

@router.message(StateFilter(AddFilm.actors))
async def process_actors(message: Message, state: FSMContext):
    actors = (message.text or "").strip()
    await state.update_data(actors=actors)
    await state.set_state(AddFilm.poster)
    await message.answer("🖼 Введіть посилання на постер (або '-' щоб пропустити)")

@router.message(StateFilter(AddFilm.poster))
async def process_poster(message: Message, state: FSMContext):
    poster = (message.text or "").strip()
    data = await state.get_data()
    
    # Додаємо фільм до бази
    new_film = db.add_film(
        title=data['title'],
        genre=data['genre'],
        description=data['description'],
        actors=data['actors'],
        poster=poster if poster != '-' else ""
    )
    
    await message.answer(f"✅ Фільм '{new_film['title']}' успішно додано!")
    await state.clear()

# --- РЕДАГУВАННЯ ФІЛЬМІВ ---

@router.callback_query(F.data.startswith("edit_"))
async def process_edit(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Тільки адмін може редагувати фільми")
        return
    
    film_id = int(callback.data.split("_")[1])
    film = db.get_film_by_id(film_id)
    if not film:
        await callback.message.answer("❌ Фільм не знайдено")
        await callback.answer()
        return
    
    kb = edit_keyboard(film_id)
    await callback.message.answer("✏️ Оберіть поле для редагування:", reply_markup=kb.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("editfield_"))
async def process_edit_field(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Тільки адмін може редагувати фільми")
        return
    
    parts = callback.data.split("_")
    film_id = int(parts[1])
    field = parts[2]
    
    film = db.get_film_by_id(film_id)
    if not film:
        await callback.message.answer("❌ Фільм не знайдено")
        await callback.answer()
        return
    
    # Зберігаємо дані для редагування
    await state.update_data(film_id=film_id, field=field)
    await state.set_state(EditFilm.new_value)
    
    field_names = {
        'title': 'назву',
        'genre': 'жанр', 
        'description': 'опис',
        'actors': 'акторів',
        'poster': 'посилання на постер'
    }
    
    current_value = film.get(field, 'не вказано')
    await callback.message.answer(
        f"✏️ Введіть нове значення для {field_names[field]}:\n"
        f"Поточне значення: {current_value}\n\n"
        f"Щоб видалити значення, введіть '-'"
    )
    await callback.answer()

@router.message(StateFilter(EditFilm.new_value))
async def process_edit_value(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Тільки адмін може редагувати фільми")
        await state.clear()
        return
    
    data = await state.get_data()
    film_id = data['film_id']
    field = data['field']
    new_value = message.text.strip()
    
    # Оновлюємо поле
    db.update_field(film_id, field, new_value)
    
    film = db.get_film_by_id(film_id)
    await message.answer(f"✅ Поле успішно оновлено!\n\n🎬 Фільм: {film['title']}")
    await show_card(message, film)
    await state.clear()

@router.callback_query(F.data.startswith("delete_"))
async def process_delete(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Тільки адмін може видаляти фільми")
        return
    
    film_id = int(callback.data.split("_")[1])
    film = db.get_film_by_id(film_id)
    if not film:
        await callback.message.answer("❌ Фільм не знайдено")
        await callback.answer()
        return
    
    # Видаляємо фільм
    db.delete_film(film_id)
    await callback.message.answer(f"🗑️ Фільм '{film['title']}' успішно видалено!")
    await callback.answer()

# --- Пошук ---

@router.message(F.state == "waiting_for_search")
async def handle_search_input(message: Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        await message.answer("🔍 Будь ласка, введіть назву фільму для пошуку")
        return
    
    films = db.search_films(query)
    if not films:
        await message.answer("🔍 Нічого не знайдено")
        await state.clear()
        return
    
    user_id = message.from_user.id
    admin = is_admin(user_id)
    
    if len(films) == 1:
        await show_card(message, films[0])
    else:
        kb = films_keyboard(films)
        await message.answer(f"🔍 Знайдено {len(films)} фільмів:", reply_markup=kb.as_markup())
        if admin:
            await message.answer("⚙️ Як адмін, ви можете редагувати фільми, натиснувши на них")
    
    await state.clear()

# --- Загальний пошук (якщо не в режимі пошуку) ---
@router.message(F.text & ~F.text.startswith('/') & 
               ~F.text.in_(["🎬 /films", "🔎 /search", "🎭 /genres", "🎲 /random", "⭐ /favorites"]))
async def handle_general_search(message: Message):
    query = message.text.strip()
    if not query:
        return
    
    films = db.search_films(query)
    if not films:
        await message.answer("🔍 Нічого не знайдено")
        return
    
    if len(films) == 1:
        await show_card(message, films[0])
    else:
        kb = films_keyboard(films)
        await message.answer(f"🔍 Знайдено {len(films)} фільмів:", reply_markup=kb.as_markup())