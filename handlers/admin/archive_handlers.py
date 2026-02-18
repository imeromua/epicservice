# epicservice/handlers/admin/archive_handlers.py

import logging
import os
import zipfile
from collections import defaultdict
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from config import ADMIN_IDS, ARCHIVES_PATH
from handlers.admin.core import _show_admin_panel
from lexicon.lexicon import LEXICON
from utils.archive_manager import ACTIVE_DIR, get_all_archives, get_user_archives

logger = logging.getLogger(__name__)

router = Router()
router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))


# --- Адмін: список усіх юзерів з архівами ---

@router.callback_query(F.data == "admin:user_archives")
async def show_users_archives_list(callback: CallbackQuery, state: FSMContext):
    """
    Показує адміністратору список юзерів, які мають збережені списки в архіві.
    """
    await callback.answer()
    try:
        logger.info("Адмін запитує список усіх архівів")
        all_files = get_all_archives()

        if not all_files:
            await callback.answer(LEXICON.NO_USERS_WITH_ARCHIVES, show_alert=True)
            return

        # Групуємо за user_id
        users_count = defaultdict(int)
        for _, _, uid in all_files:
            users_count[uid] += 1

        buttons = []
        for uid, count in sorted(users_count.items()):
            buttons.append(
                [InlineKeyboardButton(
                    text=f"👤 User {uid} — {count} списків",
                    callback_data=f"admin:view_user:{uid}"
                )]
            )

        buttons.append(
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")]
        )

        await callback.message.edit_text(
            f"🗂 *Архіви користувачів:*\nОберіть користувача:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        await state.update_data(main_message_id=callback.message.message_id)

    except Exception as e:
        logger.error(f"Помилка при отриманні списку архівів: {e}", exc_info=True)
        await callback.answer(LEXICON.UNEXPECTED_ERROR, show_alert=True)


@router.callback_query(F.data.startswith("admin:view_user:"))
async def view_user_archive(callback: CallbackQuery, state: FSMContext):
    """
    Показує список файлів обраного користувача (адмін-вид).
    """
    await callback.answer()
    try:
        user_id = int(callback.data.split(":")[-1])
        files = get_user_archives(user_id)

        if not files:
            await callback.answer(LEXICON.USER_HAS_NO_ARCHIVES, show_alert=True)
            await show_users_archives_list(callback, state)
            return

        buttons = []
        for filename, ts in files:
            label = f"📄 {ts.strftime('%d.%m %H:%M')} — {filename}"
            buttons.append(
                [InlineKeyboardButton(
                    text=label,
                    callback_data=f"admin:send:{filename}"
                )]
            )

        # Кнопка завантажити ZIP
        buttons.append(
            [InlineKeyboardButton(
                text=f"📦 Завантажити всі (ZIP)",
                callback_data=f"download_zip:{user_id}"
            )]
        )
        buttons.append(
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:user_archives")]
        )

        await callback.message.edit_text(
            f"👤 *User {user_id} — {len(files)} списків:*\nНатисніть для отримання файлу:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        await state.update_data(main_message_id=callback.message.message_id)

    except Exception as e:
        logger.error(f"Помилка при перегляді архіву user {callback.data}: {e}", exc_info=True)
        await callback.answer(LEXICON.UNEXPECTED_ERROR, show_alert=True)


@router.callback_query(F.data.startswith("admin:send:"))
async def admin_send_file(callback: CallbackQuery, bot: Bot):
    """
    Адмін отримує окремий файл користувача.
    """
    filename = callback.data.split("admin:send:", 1)[1]
    file_path = os.path.join(ACTIVE_DIR, filename)
    await callback.answer()

    if not os.path.exists(file_path):
        await callback.answer("❌ Файл не знайдено", show_alert=True)
        return

    try:
        await bot.send_document(
            chat_id=callback.message.chat.id,
            document=FSInputFile(file_path),
            caption=f"📄 {filename}"
        )
    except Exception as e:
        logger.error(f"Помилка відправки файлу адміну {filename}: {e}", exc_info=True)
        await callback.answer(LEXICON.UNEXPECTED_ERROR, show_alert=True)


@router.callback_query(F.data.startswith("download_zip:"))
async def download_zip_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Пакує всі файли користувача в ZIP і відправляє адміну.
    """
    zip_path = None
    await callback.answer()
    try:
        user_id = int(callback.data.split(":")[-1])
        files = get_user_archives(user_id)

        if not files:
            await callback.answer("❌ Файлів немає", show_alert=True)
            return

        await callback.message.edit_text(
            f"⌛️ Пакую {len(files)} файлів для user {user_id}...",
            reply_markup=None
        )

        # Створюємо ZIP
        zip_filename = f"user_{user_id}_{datetime.now().strftime('%d-%m-%Y_%H-%M')}.zip"
        zip_path = os.path.join(ARCHIVES_PATH, zip_filename)

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for filename, _ in files:
                fp = os.path.join(ACTIVE_DIR, filename)
                if os.path.exists(fp):
                    zipf.write(fp, filename)

        await bot.send_document(
            chat_id=callback.message.chat.id,
            document=FSInputFile(zip_path),
            caption=f"📦 Архів user {user_id} ({len(files)} файлів)"
        )

        await _show_admin_panel(callback, state, bot)

    except Exception as e:
        logger.error(f"Помилка створення ZIP для user {callback.data}: {e}", exc_info=True)
        await callback.answer(LEXICON.UNEXPECTED_ERROR, show_alert=True)
    finally:
        if zip_path and os.path.exists(zip_path):
            os.remove(zip_path)
