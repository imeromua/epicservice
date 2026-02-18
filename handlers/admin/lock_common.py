# epicservice/handlers/admin/lock_common.py
"""
Спільна логіка для обробників блокування (lock) в адмін-панелі.
Використовується в import_handlers.py та report_handlers.py для уникнення дублювання.
"""
import logging

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import CallbackQuery

from lexicon.lexicon import LEXICON
from utils.force_save_helper import force_save_user_list

logger = logging.getLogger(__name__)


async def handle_lock_notify_common(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """
    Надсилає сповіщення користувачам із активними списками.
    Спільна реалізація для import та report handlers.
    """
    data = await state.get_data()
    for user_id in data.get('locked_user_ids', []):
        try:
            await bot.send_message(user_id, LEXICON.USER_SAVE_LIST_NOTIFICATION)
        except Exception as e:
            logger.warning("Не вдалося надіслати сповіщення користувачу %s: %s", user_id, e)
    await callback.answer(LEXICON.NOTIFICATIONS_SENT, show_alert=True)


async def handle_lock_force_save_common(callback: CallbackQuery, state: FSMContext, bot: Bot) -> list[bool]:
    """
    Примусово зберігає списки всіх заблокованих користувачів.
    Повертає список bool-результатів для кожного користувача.
    Спільна реалізація для import та report handlers.
    """
    await callback.message.edit_text("Почав примусове збереження списків...")
    data = await state.get_data()
    user_ids = data.get('locked_user_ids', [])

    results = []
    for user_id in user_ids:
        user_state_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
        user_state = FSMContext(storage=state.storage, key=user_state_key)
        results.append(await force_save_user_list(user_id, bot, user_state))

    return results
