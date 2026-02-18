# epicservice/keyboards/webapp.py

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def get_webapp_keyboard() -> InlineKeyboardMarkup:
    """
    Клавіатура з кнопкою для відкриття Telegram Mini App.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Відкрити додаток",
            web_app=WebAppInfo(url="https://anubis-ua.pp.ua")
        )],
        [InlineKeyboardButton(
            text="⬅️ Назад до меню",
            callback_data="main:back"
        )]
    ])
