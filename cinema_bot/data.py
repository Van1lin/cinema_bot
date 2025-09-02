import json
import random
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from config import DATA_FILE

class Database:
    """Клас для роботи з локальною JSON-базою (фільми, обране, рейтинги)."""

    def __init__(self, path: str = DATA_FILE) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        if not self.path.exists():
            self._write_data({"movies": [], "favorites": {}, "ratings": {}})

    # читання з JSON (потокобезпечно)
    def _read_data(self) -> Dict[str, Any]:
        with self._lock:
            try:
                raw = self.path.read_text(encoding="utf-8")
                return json.loads(raw) if raw else {"movies": [], "favorites": {}, "ratings": {}}
            except Exception:
                return {"movies": [], "favorites": {}, "ratings": {}}

    # запис в JSON (через тимчасовий файл)
    def _write_data(self, data: Dict[str, Any]) -> None:
        with self._lock:
            temp = self.path.with_suffix(".tmp")
            temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(self.path)

    # отримати всі фільми
    def get_films(self) -> List[Dict[str, Any]]:
        data = self._read_data()
        return list(data.get("movies", []))

    # пошук фільму за ID
    def get_film_by_id(self, film_id: int) -> Optional[Dict[str, Any]]:
        return next((m for m in self.get_films() if int(m.get("id", -1)) == int(film_id)), None)

    # випадковий фільм
    def random_film(self) -> Optional[Dict[str, Any]]:
        films = self.get_films()
        return random.choice(films) if films else None

    # пошук за текстовим запитом
    def search_films(self, query: str) -> List[Dict[str, Any]]:
        q = (query or "").strip().lower()
        if not q:
            return []
        films = self.get_films()
        return [
            m for m in films
            if q in m.get("title", "").lower()
            or q in m.get("genre", "").lower()
            or q in m.get("description", "").lower()
        ]

    # фільтрація за жанром
    def filter_by_genre(self, genre: str) -> List[Dict[str, Any]]:
        g = (genre or "").strip().lower()
        films = self.get_films()
        return [m for m in films if g in (m.get("genre", "").strip().lower())]

    # наступний ID
    def _next_id(self, films: List[Dict[str, Any]]) -> int:
        return max((f.get("id", 0) for f in films), default=0) + 1

    # додати новий фільм
    def add_film(self, title: str, genre: str, description: str = "", actors: str = "", poster: str = "") -> Dict[str, Any]:
        data = self._read_data()
        films = data.get("movies", [])
        new_film = {
            "id": self._next_id(films),
            "title": title.strip(),
            "genre": genre.strip(),
            "description": description.strip(),
            "actors": actors.strip(),
            "poster": poster.strip(),
            "rating": 0.0,
            "votes": 0
        }
        films.append(new_film)
        data["movies"] = films
        self._write_data(data)
        return new_film

    # видалити фільм
    def delete_film(self, film_id: int) -> None:
        data = self._read_data()
        data["movies"] = [m for m in data.get("movies", []) if int(m.get("id")) != int(film_id)]

        # чистимо з обраного
        for uid, lst in data.get("favorites", {}).items():
            data["favorites"][uid] = [mid for mid in lst if int(mid) != int(film_id)]

        # чистимо рейтинги
        for uid in list(data.get("ratings", {})):
            data["ratings"][uid].pop(str(film_id), None)

        self._write_data(data)

    # додати/прибрати з обраного
    def toggle_favorite(self, film_id: int, user_id: int) -> bool:
        data = self._read_data()
        favorites: Dict[str, List[int]] = data.get("favorites", {})
        key = str(user_id)
        favorites.setdefault(key, [])
        if int(film_id) in [int(x) for x in favorites[key]]:
            favorites[key] = [x for x in favorites[key] if int(x) != int(film_id)]
            added = False
        else:
            favorites[key].append(int(film_id))
            added = True
        data["favorites"] = favorites
        self._write_data(data)
        return added

    # отримати список обраних
    def get_favorites(self, user_id: int) -> List[Dict[str, Any]]:
        data = self._read_data()
        id_list = [int(x) for x in data.get("favorites", {}).get(str(user_id), [])]
        return [m for m in self.get_films() if int(m.get("id")) in id_list]

    # додати рейтинг
    def add_rating(self, film_id: int, user_id: int, rating: int) -> float:
        data = self._read_data()
        ratings: Dict[str, Dict[str, int]] = data.get("ratings", {})
        ratings.setdefault(str(user_id), {})[str(film_id)] = int(rating)

        # перерахунок середнього
        scores = [int(user_map[str(film_id)]) for user_map in ratings.values() if str(film_id) in user_map]
        average = sum(scores) / len(scores) if scores else 0.0

        for f in data.get("movies", []):
            if int(f.get("id")) == int(film_id):
                f["rating"] = round(float(average), 2)
                f["votes"] = len(scores)
                break

        data["ratings"] = ratings
        self._write_data(data)
        return float(average)

    # оновити конкретне поле (для редагування адміністратором)
    def update_field(self, film_id: int, field: str, value: str) -> None:
        if field not in {"title", "genre", "description", "actors", "poster"}:
            return
        data = self._read_data()
        for f in data.get("movies", []):
            if int(f.get("id")) == int(film_id):
                f[field] = (value.strip() if value != "-" else "")
                break
        self._write_data(data)