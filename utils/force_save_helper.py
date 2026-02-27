# epicservice/utils/force_save_helper.py

import logging
import os
import shutil

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from sqlalchemy.exc import SQLAlchemyError

from database.engine import async_session
from handlers.common import clean_previous_keyboard
from lexicon.lexicon import LEXICON
from utils.list_processor import process_and_save_list

logger = logging.getLogger(__name__)

# Директорія для архівів (та ж сама що у archive_manager.py)
ARCHIVES_DIR = os.path.join("archives", "active")


def _ensure_archives_dir():
    """Переконується що директорія archives/active існує"""
    if not os.path.exists(ARCHIVES_DIR):
        os.makedirs(ARCHIVES_DIR)
        logger.info(f"Створено директорію {ARCHIVES_DIR}")


def _move_to_archives(temp_file_path: str) -> str:
    """
    Переміщує тимчасовий файл в директорію archives/active/
    Повертає новий шлях до файлу
    """
    if not temp_file_path or not os.path.exists(temp_file_path):
        return None
    
    _ensure_archives_dir()
    
    # Генеруємо нову назву файлу в archives/active/
    filename = os.path.basename(temp_file_path)
    archive_path = os.path.join(ARCHIVES_DIR, filename)
    
    # Переміщуємо файл
    shutil.move(temp_file_path, archive_path)
    logger.info(f"Файл переміщено: {temp_file_path} -> {archive_path}")
    
    return archive_path


async def force_save_user_list(user_id: int, bot: Bot, state: FSMContext) -> bool:
    """
    Примусово зберігає тимчасовий список користувача.
    Використовується в боті з FSMContext.
    Файли зберігаються в archives/active/ і автоматично відображаються в Mini App.
    Користувач отримує повідомлення БЕЗ файлу з інструкцією.
    """
    main_list_path = None
    surplus_list_path = None
    archive_main_path = None
    archive_surplus_path = None
    
    try:
        user_state = state
        
        async with async_session() as session:
            async with session.begin():
                # Генеруємо файли (вже зберігаються в ACTIVE_DIR)
                main_list_path, surplus_list_path = await process_and_save_list(session, user_id)
                
                if not main_list_path and not surplus_list_path:
                    return True
                
                # Файли вже збережено в archives/active/ — просто фіксуємо шляхи,
                # щоб блок finally не видалив їх.
                archive_main_path = main_list_path
                archive_surplus_path = surplus_list_path

        # Прибираємо клавіатуру з попереднього головного меню користувача
        await clean_previous_keyboard(user_state, bot, user_id)
        
        # Надсилаємо повідомлення БЕЗ файлу
        message = (
            "✅ <b>Ваш список було примусово збережено адміністратором</b>\n\n"
            "📁 Файл Excel доступний у розділі:\n"
            "<b>Архів → Мої списки</b>\n\n"
            "Відкрийте Mini App для перегляду."
        )
        
        await bot.send_message(
            user_id,
            message,
            parse_mode="HTML"
        )

        logger.info(f"Примусове збереження завершено для користувача {user_id}")
        return True

    except (SQLAlchemyError, ValueError) as e:
        logger.error("Помилка транзакції при примусовому збереженні для %s: %s", user_id, e, exc_info=True)
        try:
            await bot.send_message(user_id, LEXICON.TRANSACTION_ERROR)
        except Exception as bot_error:
            logger.warning("Не вдалося надіслати повідомлення про помилку користувачу %s: %s", user_id, bot_error)
        return False
    except Exception as e:
        logger.error("Неочікувана помилка при примусовому збереженні для %s: %s", user_id, e, exc_info=True)
        try:
            await bot.send_message(user_id, LEXICON.UNEXPECTED_ERROR)
        except Exception as bot_error:
            logger.warning("Не вдалося надіслати повідомлення про помилку користувачу %s: %s", user_id, bot_error)
        return False
    finally:
        # Видаляємо ТІЛЬКИ якщо переміщення не відбулось (rollback)
        if main_list_path and os.path.exists(main_list_path) and not archive_main_path:
            os.remove(main_list_path)
        if surplus_list_path and os.path.exists(surplus_list_path) and not archive_surplus_path:
            os.remove(surplus_list_path)


async def force_save_user_list_web(user_id: int, bot: Bot) -> bool:
    """
    Спрощена версія для виклику з веб-API без FSMContext.
    Файли зберігаються в archives/active/ і автоматично відображаються в Mini App.
    Користувач отримує повідомлення БЕЗ файлу з інструкцією.
    """
    main_list_path = None
    surplus_list_path = None
    archive_main_path = None
    archive_surplus_path = None
    
    try:
        async with async_session() as session:
            async with session.begin():
                # Генеруємо файли (вже зберігаються в ACTIVE_DIR)
                main_list_path, surplus_list_path = await process_and_save_list(session, user_id)

                if not main_list_path and not surplus_list_path:
                    # Файли відсутні — виходимо з транзакції перед викликом Telegram API
                    archive_main_path = None
                    archive_surplus_path = None
                else:
                    # Файли вже збережено в archives/active/ — просто фіксуємо шляхи,
                    # щоб блок finally не видалив їх.
                    archive_main_path = main_list_path
                    archive_surplus_path = surplus_list_path

        # Телеграм-повідомлення надсилаємо ПІСЛЯ завершення транзакції
        if not archive_main_path and not archive_surplus_path:
            await bot.send_message(user_id, "⚠️ У вас немає активного списку для збереження")
            return True
        
        # Надсилаємо повідомлення БЕЗ файлу
        message = (
            "✅ <b>Ваш список було примусово збережено адміністратором</b>\n\n"
            "📁 Файл Excel доступний у розділі:\n"
            "<b>Архів → Мої списки</b>\n\n"
            "Відкрийте Mini App для перегляду та завантаження."
        )
        
        await bot.send_message(
            user_id,
            message,
            parse_mode="HTML"
        )
        
        logger.info(f"Примусове збереження (веб) завершено для користувача {user_id}")
        return True

    except (SQLAlchemyError, ValueError) as e:
        logger.error("Помилка транзакції при примусовому збереженні (веб) для %s: %s", user_id, e, exc_info=True)
        try:
            await bot.send_message(user_id, LEXICON.TRANSACTION_ERROR)
        except Exception as bot_error:
            logger.warning("Не вдалося надіслати повідомлення про помилку користувачу %s: %s", user_id, bot_error)
        return False
    except Exception as e:
        logger.error("Неочікувана помилка при примусовому збереженні (веб) для %s: %s", user_id, e, exc_info=True)
        try:
            await bot.send_message(user_id, LEXICON.UNEXPECTED_ERROR)
        except Exception as bot_error:
            logger.warning("Не вдалося надіслати повідомлення про помилку користувачу %s: %s", user_id, bot_error)
        return False
    finally:
        # Видаляємо ТІЛЬКИ якщо переміщення не відбулось (rollback)
        if main_list_path and os.path.exists(main_list_path) and not archive_main_path:
            os.remove(main_list_path)
        if surplus_list_path and os.path.exists(surplus_list_path) and not archive_surplus_path:
            os.remove(surplus_list_path)
