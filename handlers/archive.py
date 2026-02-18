# epicservice/handlers/archive.py

import logging
import os

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from handlers.user.list_management import back_to_main_menu
from lexicon.lexicon import LEXICON
from utils.archive_manager import ACTIVE_DIR, get_user_archives

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "main:archive")
async def show_archive_handler(callback: CallbackQuery, state: FSMContext):
    """
    Показує архів збережених списків користувача (з файлової системи).
    """
    user_id = callback.from_user.id
    await callback.answer()

    try:
        logger.info(f"Користувач {user_id} запитує свій архів")
        files = get_user_archives(user_id)

        if not files:
            await callback.answer(LEXICON.NO_ARCHIVED_LISTS, show_alert=True)
            return

        # Будуємо inline-клавіатуру — кожен файл окремою кнопкою
        buttons = []
        for filename, ts in files:
            label = f"📄 {ts.strftime('%d.%m %H:%M')} — {filename}"
            buttons.append(
                [InlineKeyboardButton(
                    text=label,
                    callback_data=f"archive:send:{filename}"
                )]
            )

        buttons.append(
            [InlineKeyboardButton(text=LEXICON.BUTTON_BACK_TO_MAIN_MENU, callback_data="main:back")]
        )

        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(
            f"🗂 *Ваш архів ({len(files)} списків):*\nНатисніть на список, щоб отримати файл:",
            reply_markup=kb
        )
        await state.update_data(main_message_id=callback.message.message_id)

    except Exception as e:
        logger.error(f"Неочікувана помилка при перегляді архіву {user_id}: {e}", exc_info=True)
        await callback.message.answer(LEXICON.UNEXPECTED_ERROR)


@router.callback_query(F.data.startswith("archive:send:"))
async def send_archive_file(callback: CallbackQuery, bot: Bot):
    """
    Відправляє користувачу обраний Excel файл з архіву.
    """
    filename = callback.data.split("archive:send:", 1)[1]
    file_path = os.path.join(ACTIVE_DIR, filename)
    await callback.answer()

    if not os.path.exists(file_path):
        logger.warning(f"Файл не знайдено: {file_path}")
        await callback.answer("❌ Файл не знайдено", show_alert=True)
        return

    try:
        await bot.send_document(
            chat_id=callback.message.chat.id,
            document=FSInputFile(file_path),
            caption=f"📄 {filename}"
        )
        logger.info(f"Відправлено файл користувачу {callback.from_user.id}: {filename}")
    except Exception as e:
        logger.error(f"Помилка відправки файлу {filename}: {e}", exc_info=True)
        await callback.answer(LEXICON.UNEXPECTED_ERROR, show_alert=True)
