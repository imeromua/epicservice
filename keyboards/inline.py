# epicservice/keyboards/inline.py

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from lexicon.lexicon import LEXICON


def get_confirmation_kb(confirm_callback: str, cancel_callback: str) -> InlineKeyboardMarkup:
    """
    Універсальна клавіатура підтвердження Так/Ні.
    Використовується для підтвердження критичних операцій.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=LEXICON.BUTTON_CONFIRM_YES, callback_data=confirm_callback),
            InlineKeyboardButton(text=LEXICON.BUTTON_CONFIRM_NO, callback_data=cancel_callback),
        ]]
    )


def get_admin_lock_kb(action: str) -> InlineKeyboardMarkup:
    """
    Клавіатура попередження про активні списки користувачів.
    Пропонує повідомити або примусово зберегти списки перед операцією.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text=LEXICON.BUTTON_NOTIFY_USERS,
                callback_data=f"lock:notify:{action}"
            ),
            InlineKeyboardButton(
                text=LEXICON.BUTTON_FORCE_SAVE,
                callback_data=f"lock:force_save:{action}"
            )
        ]]
    )


def get_notify_confirmation_kb() -> InlineKeyboardMarkup:
    """
    Клавіатура запиту розсилки користувачам.
    Використовується після імпорту для підтвердження сповіщення.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text=LEXICON.BUTTON_YES_NOTIFY,
                callback_data="notify_confirm:yes"
            ),
            InlineKeyboardButton(
                text=LEXICON.BUTTON_NO_NOTIFY,
                callback_data="notify_confirm:no"
            ),
        ]]
    )
