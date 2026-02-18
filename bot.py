import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from sqlalchemy import text

from config import BOT_TOKEN, REDIS_ENABLED, REDIS_URL
from database.engine import async_session
from handlers import (archive, common, error_handler, user_search)
from handlers.admin import (archive_handlers as admin_archive,
                            core as admin_core,
                            import_handlers as admin_import,
                            report_handlers as admin_reports)
from handlers.user import (list_editing, list_management, list_saving)
from middlewares.logging_middleware import LoggingMiddleware


async def set_main_menu(bot: Bot):
    """Видаляє меню команд бота (передає порожній список)."""
    await bot.set_my_commands([])


async def main():
    """Головна асинхронна функція для ініціалізації та запуску бота."""

    # --- Налаштування логування (єдиний виклик basicConfig у всьому проекті) ---
    log_format = (
        "%(asctime)s - %(levelname)s - "
        "[User:%(user_id)s | Update:%(update_id)s] - "
        "%(name)s - %(message)s"
    )
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log', mode='a')
        ]
    )
    # Додаємо UserContextFilter до кореневого логера, щоб усі модулі мали user_id/update_id
    from middlewares.logging_middleware import UserContextFilter
    root_logger = logging.getLogger()
    if not any(isinstance(f, UserContextFilter) for f in root_logger.filters):
        root_logger.addFilter(UserContextFilter())

    logger = logging.getLogger(__name__)

    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN не знайдено! Перевірте .env файл.")
        sys.exit(1)

    # --- Перевірка підключення до БД ---
    try:
        async with async_session() as session:
            await session.execute(text('SELECT 1'))
        logger.info("Підключення до бази даних успішне.")
    except Exception as e:
        logger.critical("Помилка підключення до бази даних: %s", e, exc_info=True)
        sys.exit(1)

    # --- Ініціалізація Storage (Redis або Memory залежно від REDIS_ENABLED) ---
    redis = None
    if REDIS_ENABLED:
        try:
            redis = Redis.from_url(REDIS_URL)
            await redis.ping()
            storage = RedisStorage(redis=redis)
            logger.info("Підключення до Redis успішне: %s", REDIS_URL)
        except Exception as e:
            logger.critical("Помилка підключення до Redis: %s", e, exc_info=True)
            sys.exit(1)
    else:
        storage = MemoryStorage()
        logger.warning("Використовується MemoryStorage — дані FSM не збережуться після перезапуску!")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode="Markdown",
            link_preview_is_disabled=True
        )
    )

    dp = Dispatcher(storage=storage)
    dp.update.middleware(LoggingMiddleware())

    # --- Реєстрація роутерів ---
    dp.include_router(error_handler.router)
    dp.include_router(admin_core.router)
    dp.include_router(admin_import.router)
    dp.include_router(admin_reports.router)
    dp.include_router(admin_archive.router)
    dp.include_router(common.router)
    dp.include_router(archive.router)
    dp.include_router(list_management.router)
    dp.include_router(list_editing.router)
    dp.include_router(list_saving.router)
    dp.include_router(user_search.router)

    try:
        await set_main_menu(bot)
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Бот запускається...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical("Критична помилка під час роботи бота: %s", e, exc_info=True)
    finally:
        logger.info("Завершення роботи бота...")
        await bot.session.close()
        if redis is not None:
            await redis.aclose()
        logger.info("Сесія бота закрита.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот зупинено користувачем.")
    except Exception as e:
        logging.critical("Неочікувана помилка на верхньому рівні: %s", e, exc_info=True)
        sys.exit(1)
