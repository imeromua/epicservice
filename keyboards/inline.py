# epicservice/keyboards/inline.py

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.models import Product, TempList
from lexicon.lexicon import LEXICON


def get_user_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=LEXICON.INLINE_BUTTON_NEW_LIST,
                    callback_data="main:new_list"
                ),
                InlineKeyboardButton(
                    text=LEXICON.INLINE_BUTTON_MY_LIST,
                    callback_data="main:my_list"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=LEXICON.INLINE_BUTTON_ARCHIVE,
                    callback_data="main:archive"
                )
            ],
        ]
    )

def get_admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=LEXICON.INLINE_BUTTON_NEW_LIST,
                    callback_data="main:new_list"
                ),
                InlineKeyboardButton(
                    text=LEXICON.INLINE_BUTTON_MY_LIST,
                    callback_data="main:my_list"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=LEXICON.INLINE_BUTTON_ADMIN_PANEL,
                    callback_data="admin:main"
                )
            ],
            [
                InlineKeyboardButton(
                    text=LEXICON.INLINE_BUTTON_ARCHIVE,
                    callback_data="main:archive"
                )
            ],
        ]
    )

def get_admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=LEXICON.BUTTON_IMPORT_PRODUCTS, callback_data="admin:import_products")],
            [InlineKeyboardButton(text=LEXICON.BUTTON_EXPORT_STOCK, callback_data="admin:export_stock")],
            [InlineKeyboardButton(text=LEXICON.EXPORT_COLLECTED_BUTTON, callback_data="admin:export_collected")],
            [InlineKeyboardButton(text=LEXICON.BUTTON_SUBTRACT_COLLECTED, callback_data="admin:subtract_collected")],
            [InlineKeyboardButton(text=LEXICON.BUTTON_USER_ARCHIVES, callback_data="admin:user_archives")],
            [InlineKeyboardButton(text=LEXICON.BUTTON_DELETE_ALL_LISTS, callback_data="admin:delete_all_lists")],
            [InlineKeyboardButton(text=LEXICON.BUTTON_BACK_TO_MAIN_MENU, callback_data="main:back")]
        ]
    )

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
    else:
        keyboard.append([
            InlineKeyboardButton(text=LEXICON.BUTTON_BACK_TO_MAIN_MENU, callback_data="main:back")
        ])
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_search_results_kb(products: list[Product]) -> InlineKeyboardMarkup:
    keyboard = []
    for product in products:
        button_text = (product.назва[:60] + '..') if len(product.назва) > 62 else product.назва
        keyboard.append([
            InlineKeyboardButton(text=button_text, callback_data=f"product:{product.id}")
        ])
    # Додаємо кнопку "Головне меню" в кінець списку результатів
    keyboard.append([
         InlineKeyboardButton(text=LEXICON.BUTTON_BACK_TO_MAIN_MENU, callback_data="main:back")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_product_card_kb(
    product_id: int,
    current_qty: int = 1, # Це "обрана кількість" на селекторі (за замовчуванням 1)
    price: float = 0.0,
    max_qty: int = 9999, # Скільки МОЖНА додати (available)
    search_query: str | None = None
) -> InlineKeyboardMarkup:
    """
    Генерує інтерактивну клавіатуру картки товару (Selector Mode).
    Рядок 1: - [X шт] + (Вибір кількості для додавання)
    Рядок 2: 🛒 Додати до списку (X шт)
    Рядок 3: Додати все (Max шт) (якщо доступно > 1)
    Рядок 4: Навігація
    """
    
    keyboard = []
    
    price_str = str(price)
    
    # 1. Рядок вибору кількості
    # Callback data: selector:inc/dec:product_id:current_val:max_val
    
    center_text = f"📝 {current_qty} шт" 
    
    qty_row = [
        InlineKeyboardButton(
            text="➖",
            callback_data=f"selector:dec:{product_id}:{current_qty}:{max_qty}"
        ),
        InlineKeyboardButton(
            text=center_text,
            callback_data=f"qty_manual_input:{product_id}" # Ручне введення для селектора
        ),
        InlineKeyboardButton(
            text="➕",
            callback_data=f"selector:inc:{product_id}:{current_qty}:{max_qty}"
        )
    ]
    keyboard.append(qty_row)
    
    # 2. Кнопка ПІДТВЕРДЖЕННЯ (Додати до списку)
    # Callback data: add_to_list:product_id:quantity
    
    total_price_for_selection = current_qty * price
    add_btn_text = f"🛒 Додати до списку ({total_price_for_selection:.2f} грн)"
    
    keyboard.append([
        InlineKeyboardButton(
            text=add_btn_text,
            callback_data=f"add_to_list:{product_id}:{current_qty}"
        )
    ])
    
    # 3. Кнопка "Додати все" (Якщо на складі є більше ніж те, що ми зараз вибрали, і більше 0)
    # Тут max_qty - це скільки ВІЛЬНО на складі (available_for_anyone)
    if max_qty > 0 and max_qty != current_qty:
        keyboard.append([
            InlineKeyboardButton(
                text=LEXICON.BUTTON_ADD_ALL.format(quantity=max_qty),
                callback_data=f"add_to_list:{product_id}:{max_qty}"
            )
        ])
    
    # 4. Навігація
    nav_row = []
    if search_query:
        nav_row.append(
            InlineKeyboardButton(
                text=LEXICON.BUTTON_BACK_TO_SEARCH,
                callback_data="back_to_results"
            )
        )
        
    nav_row.append(
        InlineKeyboardButton(
            text=LEXICON.BUTTON_BACK_TO_MAIN_MENU,
            callback_data="main:back"
        )
    )
    keyboard.append(nav_row)

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

def get_my_list_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=LEXICON.SAVE_LIST_BUTTON,
                    callback_data="save_list"
                ),
                InlineKeyboardButton(
                    text=LEXICON.EDIT_LIST_BUTTON,
                    callback_data="edit_list:start"
                ),
                InlineKeyboardButton(
                    text=LEXICON.CANCEL_LIST_BUTTON,
                    callback_data="cancel_list:confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    text=LEXICON.BUTTON_BACK_TO_MAIN_MENU,
                    callback_data="main:back"
                )
            ]
        ]
    )

def get_list_for_editing_kb(temp_list: list[TempList]) -> InlineKeyboardMarkup:
    keyboard = []
    for item in temp_list:
        button_text = f"✏️ {item.product.артикул} ({item.quantity} шт.)"
        keyboard.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"edit_item:{item.product.id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="✅ Завершити редагування", callback_data="edit_list:finish")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
