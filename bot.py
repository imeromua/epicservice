import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from redis.asyncio import Redis
from sqlalchemy import text

from config import BOT_TOKEN, REDIS_ENABLED, REDIS_URL
from database.engine import async_session
from handlers import common, error_handler, webapp_handler
from handlers.admin import (archive_handlers as admin_archive,
                            core as admin_core,
                            import_handlers as admin_import,
                            report_handlers as admin_reports)
from middlewares.logging_middleware import LoggingMiddleware
from utils.archive_manager import cleanup_trash, ensure_archive_dirs


async def set_main_menu(bot: Bot):
    """Видаляє меню команд бота (передає порожній список)."""
    await bot.set_my_commands([])


async def scheduled_cleanup():
    """
    Щодобове очищення trash від файлів старіше 14 днів.
    """
    logger = logging.getLogger(__name__)
    try:
        logger.info("Запуск щодобового очищення trash...")
        cleanup_trash(days=14)
    except Exception as e:
        logger.error(f"Помилка при щодобовому очищенні trash: {e}", exc_info=True)


async def main():
    """Головна асинхронна функція для ініціалізації та запуску бота."""

    # --- Налаштування логування (єдиний виклик basicConfig у всьому проекті) ---
    log_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log', mode='a')
        ]
    )

    logger = logging.getLogger(__name__)

    if not BOT_TOKEN:
        logger.critical("БОТ_TOKEN не знайдено! Перевірте .env файл.")
        sys.exit(1)

    # --- Перевірка та створення архівних папок ---
    ensure_archive_dirs()

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

    # --- Ініціалізація Scheduler для автоочищення ---
    scheduler = AsyncIOScheduler()
    # Щодоби о 03:00 викликаємо cleanup_trash
    scheduler.add_job(
        scheduled_cleanup,
        trigger=CronTrigger(hour=3, minute=0),
        id="daily_trash_cleanup",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Щодобовий scheduler запущено (очищення trash о 03:00)")

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
    # Порядок важливий: спочатку error handler, потім admin, потім common
    dp.include_router(error_handler.router)
    
    # Адміністративні роутери
    dp.include_router(admin_core.router)
    dp.include_router(admin_import.router)
    dp.include_router(admin_reports.router)
    dp.include_router(admin_archive.router)
    
    # Загальні роутери (для всіх користувачів)
    dp.include_router(common.router)  # /start і кнопка Адмінка
    dp.include_router(webapp_handler.router)  # Web App handler
    
    # ВИДАЛЕНО: archive, user_search, list_management, list_editing, list_saving
    # Причина: весь user-функціонал тепер у webapp (Mini App)

    try:
        await set_main_menu(bot)
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Бот запускається...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical("Критична помилка під час роботи бота: %s", e, exc_info=True)
    finally:
        logger.info("Завершення роботи бота...")
        scheduler.shutdown(wait=False)
        logger.info("Scheduler зупинено")
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
