# epicservice/handlers/admin/core.py

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery

from config import ADMIN_IDS
from database.orm import orm_delete_all_saved_lists_sync
from keyboards.inline import get_confirmation_kb
from lexicon.lexicon import LEXICON

# Налаштовуємо логер
logger = logging.getLogger(__name__)

# Створюємо роутер
router = Router()
router.message.filter(F.from_user.id.in_(ADMIN_IDS))
router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))


class AdminCoreStates(StatesGroup):
    confirm_delete_all_lists = State()


# --- Сценарій видалення всіх списків ---

@router.callback_query(F.data == "admin:delete_all_lists")
async def delete_all_lists_confirm_handler(callback: CallbackQuery, state: FSMContext):
    """
    Перший крок сценарію видалення. Запитує підтвердження.
    """
    await callback.message.edit_text(
        LEXICON.DELETE_ALL_LISTS_CONFIRM,
        reply_markup=get_confirmation_kb(
            "confirm_delete_all_yes", "admin:main" # Кнопка "Ні" тепер повертає в меню
        ),
    )
    await state.set_state(AdminCoreStates.confirm_delete_all_lists)
    await callback.answer()


@router.callback_query(AdminCoreStates.confirm_delete_all_lists, F.data == "confirm_delete_all_yes")
async def delete_all_lists_confirmed_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Обробляє позитивне підтвердження.
    """
    await state.set_state(None)

    loop = asyncio.get_running_loop()
    deleted_count = await loop.run_in_executor(None, orm_delete_all_saved_lists_sync)

    if deleted_count > 0:
        await callback.answer(
            LEXICON.DELETE_ALL_LISTS_SUCCESS.format(count=deleted_count),
            show_alert=True
        )
    else:
        await callback.answer(LEXICON.NO_LISTS_TO_DELETE)

    # Просто повідомляємо - БЕЗ КНОПОК
    await callback.message.edit_text("✅ Списки видалено.")
