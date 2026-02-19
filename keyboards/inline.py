# epicservice/keyboards/inline.py

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from lexicon.lexicon import LEXICON


def get_admin_main_kb() -> InlineKeyboardMarkup:
    """
    Адміністративна панель: тільки необхідні функції.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=LEXICON.BUTTON_IMPORT_PRODUCTS, callback_data="admin:import_products")],
            [InlineKeyboardButton(text=LEXICON.BUTTON_EXPORT_STOCK, callback_data="admin:export_stock")],
            [InlineKeyboardButton(text=LEXICON.EXPORT_COLLECTED_BUTTON, callback_data="admin:export_collected")],
            [InlineKeyboardButton(text=LEXICON.BUTTON_SUBTRACT_COLLECTED, callback_data="admin:subtract_collected")],
            [InlineKeyboardButton(text=LEXICON.BUTTON_USER_ARCHIVES, callback_data="admin:user_archives")],
            [InlineKeyboardButton(text=LEXICON.BUTTON_DELETE_ALL_LISTS, callback_data="admin:delete_all_lists")],
        ]
    )


def get_admin_panel_kb() -> InlineKeyboardMarkup:
    """
    Дублікат get_admin_main_kb для зворотної сумісності.
    """
    return get_admin_main_kb()


def get_users_with_archives_kb(users: list) -> InlineKeyboardMarkup:
    keyboard = []
    for user_id, lists_count in users:
        button_text = LEXICON.BUTTON_USER_LIST_ITEM.format(
            user_id=user_id, lists_count=lists_count
        )
        keyboard.append([
            InlineKeyboardButton(text=button_text, callback_data=f"admin:view_user:{user_id}")
        ])

    keyboard.append([
        InlineKeyboardButton(text=LEXICON.BUTTON_BACK_TO_ADMIN_PANEL, callback_data="admin:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_archive_kb(user_id: int, is_admin_view: bool = False) -> InlineKeyboardMarkup:
    keyboard = [[
        InlineKeyboardButton(text=LEXICON.BUTTON_PACK_IN_ZIP, callback_data=f"download_zip:{user_id}")
    ]]
    
    if is_admin_view:
        keyboard.append([
            InlineKeyboardButton(text=LEXICON.BUTTON_BACK_TO_USER_LIST, callback_data="admin:user_archives")
        ])
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirmation_kb(confirm_callback: str, cancel_callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=LEXICON.BUTTON_CONFIRM_YES, callback_data=confirm_callback),
            InlineKeyboardButton(text=LEXICON.BUTTON_CONFIRM_NO, callback_data=cancel_callback),
        ]]
    )


def get_admin_lock_kb(action: str) -> InlineKeyboardMarkup:
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
