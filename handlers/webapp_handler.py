# epicservice/handlers/webapp_handler.py

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from keyboards.webapp import get_webapp_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "main:webapp")
async def open_webapp(callback: CallbackQuery, state: FSMContext):
    """
    Відкриває клавіатуру з кнопкою для запуску Telegram Mini App.
    """
    try:
        text = (
            "🚀 *Веб-додаток EpicService*\n\n"
            "Натисніть кнопку нижче, щоб відкрити повноцінний інтерфейс в одному вікні:\n\n"
            "• Пошук товарів\n"
            "• Управління списками\n"
            "• Перегляд архіву\n\n"
            "Все без сміття в чаті! 🎉"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_webapp_keyboard()
        )
        await state.update_data(main_message_id=callback.message.message_id)
        await callback.answer()
        
        logger.info(f"Користувач {callback.from_user.id} відкриває Web App")
        
    except Exception as e:
        logger.error(f"Помилка відкриття webapp: {e}", exc_info=True)
        await callback.answer("❌ Помилка відкриття додатку", show_alert=True)
