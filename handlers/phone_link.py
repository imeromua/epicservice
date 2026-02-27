# handlers/phone_link.py
"""
Обробник Telegram для прив'язки номера телефону до облікового запису.
Використовується для OTP-автентифікації Android-додатку.
"""

import logging
import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    Contact,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from database.orm.users import orm_get_user_by_id, orm_set_user_phone

logger = logging.getLogger(__name__)

router = Router()

# Клавіатура для запиту контакту
_SHARE_CONTACT_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📱 Поділитися номером", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

# Регулярний вираз для перевірки українського номера
_UA_PHONE_RE = re.compile(r"^\+380\d{9}$")


def _normalize_phone(phone: str) -> str:
    """Нормалізує номер до формату +380XXXXXXXXX."""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("380") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("80") and len(digits) == 11:
        return f"+3{digits}"
    if len(digits) == 10 and digits.startswith("0"):
        return f"+38{digits}"
    return f"+{digits}" if not phone.startswith("+") else phone


@router.message(Command("linkphone"))
async def cmd_linkphone(message: Message):
    """
    Команда /linkphone — просить користувача поділитися номером телефону.
    Прив'язаний номер використовується для входу в Android-додаток.
    """
    user = await orm_get_user_by_id(message.from_user.id)
    if user and user.phone:
        await message.answer(
            f"📱 Ваш номер вже прив'язано: *{user.phone}*\n\n"
            "Якщо хочете змінити — натисніть кнопку нижче.",
            parse_mode="Markdown",
            reply_markup=_SHARE_CONTACT_KB,
        )
    else:
        await message.answer(
            "📱 Для входу в Android-додаток необхідно прив'язати номер телефону.\n\n"
            "Натисніть кнопку нижче, щоб поділитися своїм номером:",
            reply_markup=_SHARE_CONTACT_KB,
        )


@router.message(F.contact)
async def handle_contact(message: Message):
    """Обробляє отриманий контакт та зберігає номер телефону."""
    contact: Contact = message.contact

    # Перевіряємо що контакт належить самому користувачу
    if contact.user_id != message.from_user.id:
        await message.answer(
            "⚠️ Будь ласка, поділіться власним номером телефону.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    phone = _normalize_phone(contact.phone_number)

    if not _UA_PHONE_RE.match(phone):
        await message.answer(
            "⚠️ Підтримуються лише українські номери (+380...).\n"
            "Будь ласка, спробуйте ще раз.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    try:
        await orm_set_user_phone(message.from_user.id, phone)
        logger.info("Номер %s прив'язано до user_id=%s", phone, message.from_user.id)
        await message.answer(
            f"✅ Номер *{phone}* успішно прив'язано до вашого облікового запису!\n\n"
            "Тепер ви можете входити в Android-додаток EpicService за цим номером.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
    except Exception as exc:
        logger.error("Помилка прив'язки номера %s: %s", phone, exc)
        await message.answer(
            "❌ Не вдалося зберегти номер. Можливо, цей номер вже прив'язаний до іншого облікового запису.\n"
            "Спробуйте ще раз або зверніться до адміністратора.",
            reply_markup=ReplyKeyboardRemove(),
        )
