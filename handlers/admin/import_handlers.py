# epicservice/handlers/admin/import_handlers.py

import asyncio
import logging
import os
import tempfile
from typing import List

import pandas as pd
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)
from sqlalchemy.exc import SQLAlchemyError

from config import ADMIN_IDS
from database.orm import (orm_get_all_products_sync, orm_get_all_users_sync,
                          orm_get_users_with_active_lists, orm_smart_import)
from database.orm.products import SmartColumnMapper
from handlers.admin.core import _show_admin_panel
from handlers.admin.lock_common import handle_lock_notify_common, handle_lock_force_save_common
from keyboards.inline import (get_admin_lock_kb, get_admin_main_kb,
                              get_notify_confirmation_kb, get_user_main_kb)
from lexicon.lexicon import LEXICON
from utils.force_save_helper import force_save_user_list

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(F.from_user.id.in_(ADMIN_IDS))
router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))


class AdminImportStates(StatesGroup):
    waiting_for_import_file = State()
    lock_confirmation = State()
    notify_confirmation = State()


def _validate_excel_columns(df: pd.DataFrame) -> tuple[bool, str]:
    """Використовує SmartColumnMapper для перевірки наявності необхідних колонок."""
    mapping = SmartColumnMapper.map_columns(df)
    has_identity = "article" in mapping or "name" in mapping
    has_quantity = "quantity" in mapping or "stock_sum" in mapping
    if not has_identity:
        return False, "Не знайдено колонку з Артикулом або Назвою товару."
    if not has_quantity:
        return False, "Не знайдено колонку з Кількістю або Сумою залишку."
    return True, ""


def _format_admin_report(result: dict) -> str:
    if not result:
        return "❌ Помилка імпорту. Перевірте формат файлу."
    report_lines = [
        LEXICON.IMPORT_REPORT_TITLE,
        LEXICON.IMPORT_REPORT_ADDED.format(added=result.get('added', 0)),
        LEXICON.IMPORT_REPORT_UPDATED.format(updated=result.get('updated', 0)),
        LEXICON.IMPORT_REPORT_DEACTIVATED.format(deactivated=result.get('deactivated', 0)),
        LEXICON.IMPORT_REPORT_REACTIVATED.format(reactivated=result.get('reactivated', 0)),
        LEXICON.IMPORT_REPORT_TOTAL.format(total=result.get('total_in_db', 0)),
    ]
    dep_stats = result.get('department_stats', {})
    if dep_stats:
        report_lines.append("\n📁 *По відділах:*")
        for dep, count in sorted(dep_stats.items()):
            report_lines.append(f"  • Відділ {dep}: {count} шт.")
    return "\n".join(report_lines)


async def broadcast_import_update(bot: Bot, result: dict):
    loop = asyncio.get_running_loop()
    try:
        user_ids = await loop.run_in_executor(None, orm_get_all_users_sync)
        if not user_ids:
            logger.info("Користувачі для розсилки не знайдені.")
            return

        all_products = await loop.run_in_executor(None, orm_get_all_products_sync)
        total_sum = sum(p.сума_залишку for p in all_products if p.сума_залишку)

        summary_part = LEXICON.USER_IMPORT_NOTIFICATION_SUMMARY.format(
            total_in_db=result.get('total_in_db', 0),
            total_sum=f"{total_sum:,.2f}".replace(",", " ")
        )
        details_part = LEXICON.USER_IMPORT_NOTIFICATION_DETAILS.format(
            added=result.get('added', 0),
            updated=result.get('updated', 0),
            deactivated=result.get('deactivated', 0)
        )
        departments_part = LEXICON.USER_IMPORT_NOTIFICATION_DEPARTMENTS_TITLE
        dep_stats = result.get('department_stats', {})
        departments_lines = [
            LEXICON.USER_IMPORT_NOTIFICATION_DEPARTMENT_ITEM.format(dep_id=dep_id, count=count)
            for dep_id, count in sorted(dep_stats.items())
        ]
        message_text = (
            LEXICON.USER_IMPORT_NOTIFICATION_TITLE + summary_part + "\n" +
            details_part + "\n" + departments_part + "\n".join(departments_lines)
        )

        sent_count = 0
        for user_id in user_ids:
            try:
                kb = get_admin_main_kb() if user_id in ADMIN_IDS else get_user_main_kb()
                await bot.send_message(user_id, message_text, reply_markup=kb)
                sent_count += 1
            except Exception as e:
                logger.warning("Не вдалося надіслати сповіщення користувачу %s: %s", user_id, e)

        logger.info("Розсилку завершено. Надіслано %d/%d повідомлень.", sent_count, len(user_ids))
    except Exception as e:
        logger.error("Критична помилка під час розсилки: %s", e, exc_info=True)


async def proceed_with_import(message: Message, state: FSMContext, bot: Bot, is_after_force_save: bool = False):
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=LEXICON.BUTTON_BACK_TO_ADMIN_PANEL, callback_data="admin:main")
    ]])
    if is_after_force_save:
        await message.edit_text("Списки збережено. Тепер, будь ласка, надішліть файл.")
        sent_message = await message.answer(LEXICON.IMPORT_PROMPT, reply_markup=back_kb)
        await state.update_data(main_message_id=sent_message.message_id)
    else:
        await message.edit_text(LEXICON.IMPORT_PROMPT, reply_markup=back_kb)
        await state.update_data(main_message_id=message.message_id)
    await state.set_state(AdminImportStates.waiting_for_import_file)


@router.callback_query(F.data == "admin:import_products")
async def start_import_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        active_users = await orm_get_users_with_active_lists()
        if not active_users:
            await proceed_with_import(callback.message, state, bot)
            return
        users_info = "\n".join([f"- Користувач `{user_id}` (позицій: {count})" for user_id, count in active_users])
        await state.update_data(action_to_perform='import', locked_user_ids=[uid for uid, _ in active_users])
        await state.set_state(AdminImportStates.lock_confirmation)
        await callback.message.edit_text(
            LEXICON.ACTIVE_LISTS_BLOCK.format(users_info=users_info),
            reply_markup=get_admin_lock_kb(action='import')
        )
        await callback.answer("Дію заблоковано", show_alert=True)
    except Exception as e:
        logger.error("Помилка при старті імпорту: %s", e, exc_info=True)
        await callback.answer(LEXICON.UNEXPECTED_ERROR, show_alert=True)


@router.callback_query(AdminImportStates.lock_confirmation, F.data.startswith("lock:notify:"))
async def handle_lock_notify(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await handle_lock_notify_common(callback, state, bot)


@router.callback_query(AdminImportStates.lock_confirmation, F.data.startswith("lock:force_save:"))
async def handle_lock_force_save(callback: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        results = await handle_lock_force_save_common(callback, state, bot)
        if not all(results):
            await callback.message.edit_text("Під час збереження виникли помилки. Спробуйте пізніше.")
            await state.set_state(None)
            return
        await callback.answer("Всі списки успішно збережено!", show_alert=True)
        data = await state.get_data()
        if data.get('action_to_perform') == 'import':
            await proceed_with_import(callback.message, state, bot, is_after_force_save=True)
    except Exception as e:
        logger.error("Помилка примусового збереження (import): %s", e, exc_info=True)
        await callback.answer(LEXICON.UNEXPECTED_ERROR, show_alert=True)


@router.message(AdminImportStates.waiting_for_import_file, F.document)
async def process_import_file(message: Message, state: FSMContext, bot: Bot):
    if not message.document.file_name.endswith((".xlsx", ".xls")):
        await message.answer(LEXICON.IMPORT_WRONG_FORMAT)
        return

    data = await state.get_data()
    try:
        await bot.delete_message(message.chat.id, data.get("main_message_id"))
    except Exception:
        pass

    await message.answer(LEXICON.IMPORT_PROCESSING)

    # Використовуємо tempfile для надійного іменування тимчасових файлів
    tmp_fd, temp_file_path = tempfile.mkstemp(suffix=".xlsx", prefix=f"import_{message.from_user.id}_")
    os.close(tmp_fd)

    try:
        await bot.download(message.document, destination=temp_file_path)
        df = await asyncio.to_thread(pd.read_excel, temp_file_path)

        is_valid, missing_cols = _validate_excel_columns(df)
        if not is_valid:
            await message.answer(LEXICON.IMPORT_INVALID_COLUMNS.format(columns=missing_cols))
            return

        await message.answer(LEXICON.IMPORT_STARTING)
        result = await orm_smart_import(df)
        if not result:
            await message.answer(LEXICON.IMPORT_SYNC_ERROR.format(error="не вдалося розпізнати дані."))
            return

        admin_report = _format_admin_report(result)
        await message.answer(admin_report)

        await state.update_data(import_result=result)
        sent_message = await message.answer(
            LEXICON.IMPORT_ASK_FOR_NOTIFICATION,
            reply_markup=get_notify_confirmation_kb()
        )
        await state.set_state(AdminImportStates.notify_confirmation)
        await state.update_data(main_message_id=sent_message.message_id)

    except SQLAlchemyError as e:
        logger.critical("Помилка БД під час імпорту: %s", e, exc_info=True)
        await message.answer(LEXICON.IMPORT_SYNC_ERROR.format(error=str(e)))
        await _show_admin_panel(message, state, bot)
    except Exception as e:
        logger.error("Критична помилка при обробці файлу імпорту: %s", e, exc_info=True)
        await message.answer(LEXICON.IMPORT_CRITICAL_READ_ERROR.format(error=str(e)))
        await _show_admin_panel(message, state, bot)
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.callback_query(AdminImportStates.notify_confirmation, F.data == "notify_confirm:yes")
async def handle_notify_yes(callback: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        await callback.message.edit_text(LEXICON.BROADCAST_STARTING)
        data = await state.get_data()
        await state.set_state(None)
        if result := data.get('import_result'):
            task = asyncio.create_task(broadcast_import_update(bot, result))
            # Логуємо помилки фонової задачі, щоб не втрачати їх
            task.add_done_callback(
                lambda t: t.exception() and logger.error(
                    "Помилка фонової розсилки: %s", t.exception(), exc_info=t.exception()
                )
            )
        await _show_admin_panel(callback, state, bot)
    finally:
        await callback.answer()


@router.callback_query(AdminImportStates.notify_confirmation, F.data == "notify_confirm:no")
async def handle_notify_no(callback: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        await callback.message.edit_text(LEXICON.BROADCAST_SKIPPED)
        await state.set_state(None)
        await _show_admin_panel(callback, state, bot)
    finally:
        await callback.answer()
