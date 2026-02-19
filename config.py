import logging
import os
from typing import List

from dotenv import load_dotenv

# Налаштування логера для цього модуля (БЕЗ basicConfig — він налаштовується тільки в bot.py)
logger = logging.getLogger(__name__)

# Завантажуємо змінні оточення з файлу .env
if not load_dotenv():
    logger.warning("Файл .env не знайдено або не вдалося завантажити. Використовуються системні змінні оточення.")


def get_required_env(var_name: str) -> str:
    """
    Отримує значення обов'язкової змінної оточення.

    Args:
        var_name: Назва змінної.

    Raises:
        ValueError: Якщо змінна оточення відсутня.

    Returns:
        Значення змінної у вигляді рядка.
    """
    value = os.getenv(var_name)
    if not value:
        error_msg = f"Критична помилка: відсутня обов'язкова змінна оточення: {var_name}"
        logger.critical(error_msg)
        raise ValueError(error_msg)
    return value


# --- Конфігурація Бота ---
BOT_TOKEN = get_required_env("BOT_TOKEN")

# URL для Mini App (WebApp)
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://epicservice.example.com")
logger.info("WebApp URL: %s", WEBAPP_URL)


def get_admin_ids() -> List[int]:
    """
    Безпечно парсить та повертає список ID адміністраторів зі змінної оточення.

    Очікує рядок формату 'ID1,ID2,ID3'. Ігнорує пусті значення та пробіли.
    У разі помилки формату повертає порожній список.

    Returns:
        Список цілих чисел (ID адміністраторів).
    """
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    if not admin_ids_str:
        logger.warning("Змінна ADMIN_IDS не задана. Адмін-панель буде недоступна.")
        return []
    try:
        return [int(admin_id.strip()) for admin_id in admin_ids_str.split(',') if admin_id.strip()]
    except ValueError as e:
        logger.warning(
            "Некоректний формат ADMIN_IDS. Очікується 'ID1,ID2,ID3'. Помилка: %s", e
        )
        return []


ADMIN_IDS = get_admin_ids()


# --- Конфігурація Бази Даних ---
def validate_db_port(port_str: str) -> int:
    """
    Валідує порт бази даних.

    Args:
        port_str: Порт у вигляді рядка.

    Raises:
        ValueError: Якщо порт не є числом або виходить за межі допустимого діапазону.

    Returns:
        Порт у вигляді цілого числа.
    """
    try:
        port_int = int(port_str)
        if not 1 <= port_int <= 65535:
            raise ValueError("Порт бази даних повинен бути в діапазоні від 1 до 65535.")
        return port_int
    except ValueError as e:
        logger.critical("Невірний формат порту БД: %s", e)
        raise


DB_USER = get_required_env("DB_USER")
DB_PASS = os.getenv("DB_PASSWORD") or os.getenv("DB_PASS")
if not DB_PASS:
    _err = "Критична помилка: відсутня обов'язкова змінна оточення: DB_PASSWORD (або DB_PASS)"
    logger.critical(_err)
    raise ValueError(_err)

DB_HOST = get_required_env("DB_HOST")
DB_PORT = validate_db_port(get_required_env("DB_PORT"))
DB_NAME = get_required_env("DB_NAME")

# Формуємо URL підключення (пароль не логується — тільки host/port/name)
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
SYNC_DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

logger.info("БД сконфігурована: %s@%s:%s/%s", DB_USER, DB_HOST, DB_PORT, DB_NAME)

# --- Конфігурація Redis ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Якщо REDIS_ENABLED=false — бот використовуватиме MemoryStorage (тільки для dev/тестів)
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"

if REDIS_ENABLED:
    logger.info("Redis увімкнено (%s:%s/%s)", REDIS_HOST, REDIS_PORT, REDIS_DB)
else:
    logger.warning("Redis ВИМКНЕНО. FSM зберігатиметься тільки в пам'яті (не для продакшену!)")

# URL підключення Redis
if REDIS_PASSWORD:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# --- Конфігурація Сховища ---
# Абсолютний шлях до папки archives відносно кореня проекту
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVES_PATH = os.path.join(BASE_DIR, "archives")
