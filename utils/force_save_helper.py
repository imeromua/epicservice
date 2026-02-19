# epicservice/utils/force_save_helper.py

import logging
import os

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from sqlalchemy.exc import SQLAlchemyError

from database.engine import async_session
from handlers.common import clean_previous_keyboard
from lexicon.lexicon import LEXICON
from utils.list_processor import process_and_save_list

logger = logging.getLogger(__name__)


async def force_save_user_list(user_id: int, bot: Bot, state: FSMContext) -> bool:
    """
    Примусово зберігає тимчасовий список користувача.
    Використовується в боті з FSMContext.
    Повідомлення надсилаються без клавіатур.
    """
    main_list_path = None
    surplus_list_path = None
    
    try:
        user_state = state
        
        async with async_session() as session:
            async with session.begin():
                main_list_path, surplus_list_path = await process_and_save_list(session, user_id)

        # Прибираємо клавіатуру з попереднього головного меню користувача
        await clean_previous_keyboard(user_state, bot, user_id)

        if not main_list_path and not surplus_list_path:
            return True
            
        if main_list_path:
            await bot.send_document(user_id, FSInputFile(main_list_path), caption=LEXICON.MAIN_LIST_SAVED)
        if surplus_list_path:
            await bot.send_document(user_id, FSInputFile(surplus_list_path), caption=LEXICON.SURPLUS_LIST_CAPTION)
        
        # Надсилаємо повідомлення без клавіатури
        await bot.send_message(
            user_id,
            "✅ Список збережено. Відкрийте Mini App для продовження роботи."
        )

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
        if main_list_path and os.path.exists(main_list_path):
            os.remove(main_list_path)
        if surplus_list_path and os.path.exists(surplus_list_path):
            os.remove(surplus_list_path)


async def force_save_user_list_web(user_id: int, bot: Bot) -> bool:
    """
    Спрощена версія для виклику з веб-API без FSMContext.
    Просто зберігає список і надсилає файли користувачу.
    Повідомлення надсилаються без клавіатур.
    """
    main_list_path = None
    surplus_list_path = None
    
    try:
        async with async_session() as session:
            async with session.begin():
                main_list_path, surplus_list_path = await process_and_save_list(session, user_id)

        if not main_list_path and not surplus_list_path:
            await bot.send_message(user_id, "⚠️ У вас немає активного списку для збереження")
            return True
            
        if main_list_path:
            await bot.send_document(user_id, FSInputFile(main_list_path), caption=LEXICON.MAIN_LIST_SAVED)
        if surplus_list_path:
            await bot.send_document(user_id, FSInputFile(surplus_list_path), caption=LEXICON.SURPLUS_LIST_CAPTION)
        
        await bot.send_message(
            user_id,
            "✅ Ваш список було примусово збережено адміністратором."
        )
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
        if main_list_path and os.path.exists(main_list_path):
            os.remove(main_list_path)
        if surplus_list_path and os.path.exists(surplus_list_path):
            os.remove(surplus_list_path)
