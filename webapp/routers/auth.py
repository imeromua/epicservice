"""
Роутер автентифікації для автономного додатку.
JWT-based login/password auth without Telegram dependency.
Phone OTP auth for Android app.
"""

import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from config import JWT_SECRET_KEY
from database.orm.users import (
    orm_create_standalone_user,
    orm_get_user_by_id,
    orm_get_user_by_login,
    orm_get_user_by_phone,
    orm_set_user_phone,
)
from utils.otp import TooManyAttemptsError, generate_otp, otp_exists, store_otp, verify_otp

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Конфігурація JWT ---
SECRET_KEY = JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
REFRESH_TOKEN_EXPIRE_DAYS = 30


# --- Pydantic моделі ---

class RegisterRequest(BaseModel):
    login: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)


class LoginRequest(BaseModel):
    login: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


# --- Допоміжні функції ---

def hash_password(password: str) -> str:
    """Хешує пароль за допомогою bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Перевіряє пароль за хешем."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_token(user_id: int, login: str, role: str, token_type: str) -> str:
    """Генерує JWT токен."""
    if token_type == "access":
        expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "user_id": user_id,
        "login": login,
        "role": role,
        "type": token_type,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str) -> int:
    """Валідує JWT токен та повертає user_id."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Невірний тип токена")
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Невірний токен")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Токен протермінований")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Невірний токен")


# --- Ендпоїнти ---

@router.post("/register")
async def register(req: RegisterRequest):
    """Реєстрація нового користувача (login/password)."""
    # Перевіряємо чи логін вже зайнятий
    existing = await orm_get_user_by_login(req.login)
    if existing:
        raise HTTPException(status_code=409, detail="Логін вже зайнятий")

    # Генеруємо унікальний ID (великий, щоб не конфліктувати з Telegram ID)
    for _ in range(10):
        user_id = 10_000_000_000 + secrets.randbelow(89_999_999_999)
        if not await orm_get_user_by_id(user_id):
            break
    else:
        raise HTTPException(status_code=500, detail="Не вдалося згенерувати унікальний ID")

    # Хешуємо пароль та створюємо користувача
    pwd_hash = hash_password(req.password)
    user = await orm_create_standalone_user(
        user_id=user_id,
        login=req.login,
        password_hash=pwd_hash,
        first_name=req.first_name,
    )

    # Генеруємо токени
    access_token = create_token(user.id, req.login, user.role, "access")
    refresh_token = create_token(user.id, req.login, user.role, "refresh")

    return JSONResponse({
        "success": True,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "login": req.login,
            "first_name": user.first_name,
            "role": user.role,
            "status": user.status,
        },
    })


@router.post("/login")
async def login(req: LoginRequest):
    """Авторизація за логіном та паролем."""
    user = await orm_get_user_by_login(req.login)
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Невірний логін або пароль")

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Невірний логін або пароль")

    # Генеруємо токени
    access_token = create_token(user.id, req.login, user.role, "access")
    refresh_token = create_token(user.id, req.login, user.role, "refresh")

    return JSONResponse({
        "success": True,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "login": user.login,
            "first_name": user.first_name,
            "role": user.role,
            "status": user.status,
        },
    })


@router.post("/refresh")
async def refresh(req: RefreshRequest):
    """Оновлення access токена за допомогою refresh токена."""
    try:
        payload = jwt.decode(req.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh токен протермінований")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Невірний refresh токен")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Невірний тип токена")

    user_id = payload.get("user_id")
    login_val = payload.get("login")
    role = payload.get("role")

    if not user_id or not login_val:
        raise HTTPException(status_code=401, detail="Невірний токен")

    # Перевіряємо що користувач все ще існує
    user = await orm_get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Користувача не знайдено")

    # Генеруємо новий access токен з актуальною роллю
    access_token = create_token(user.id, login_val, user.role, "access")

    return JSONResponse({
        "success": True,
        "access_token": access_token,
    })


@router.get("/me")
async def me(authorization: str = Header(...)):
    """Отримання інформації про поточного користувача."""
    # Витягуємо токен з заголовка "Bearer <token>"
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Невірний формат заголовка Authorization")

    token = authorization[7:]
    user_id = get_current_user(token)

    user = await orm_get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")

    return JSONResponse({
        "success": True,
        "user": {
            "id": user.id,
            "login": user.login,
            "first_name": user.first_name,
            "username": user.username,
            "role": user.role,
            "status": user.status,
        },
    })


# ---------------------------------------------------------------------------
# Phone OTP Authentication (Android App)
# ---------------------------------------------------------------------------

# Регулярний вираз для Ukrainian phone numbers (+380XXXXXXXXX)
_UA_PHONE_RE = re.compile(r"^\+380\d{9}$")

# Шаблон повідомлення OTP для Telegram-бота
_BOT_OTP_MSG = (
    "🔐 Ваш код підтвердження EpicService: *{otp}*\n\n"
    "Код дійсний 5 хвилин. Нікому не повідомляйте його."
)


def _normalize_phone(phone: str) -> str:
    """Нормалізує номер телефону до формату +380XXXXXXXXX."""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("380") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("80") and len(digits) == 11:
        return f"+3{digits}"
    if len(digits) == 10 and digits.startswith("0"):
        return f"+38{digits}"
    return f"+{digits}" if not phone.startswith("+") else phone


class PhoneRequestModel(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        normalized = _normalize_phone(v)
        if not _UA_PHONE_RE.match(normalized):
            raise ValueError("Введіть коректний номер телефону у форматі +380XXXXXXXXX")
        return normalized


class PhoneVerifyModel(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)
    otp: str = Field(..., min_length=4, max_length=8)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        normalized = _normalize_phone(v)
        if not _UA_PHONE_RE.match(normalized):
            raise ValueError("Введіть коректний номер телефону у форматі +380XXXXXXXXX")
        return normalized


def _get_redis(request: Request):
    """Повертає Redis-клієнт зі стану FastAPI-додатку."""
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        raise HTTPException(status_code=503, detail="Redis недоступний")
    return redis


async def _send_otp_via_bot(bot, chat_id: int, otp: str) -> bool:
    """Відправляє OTP-код користувачу через Telegram-бот."""
    try:
        await bot.send_message(chat_id, _BOT_OTP_MSG.format(otp=otp), parse_mode="Markdown")
        return True
    except Exception as exc:
        logger.warning("Не вдалося надіслати OTP через бот (chat_id=%s): %s", chat_id, exc)
        return False


@router.post("/phone/request")
async def phone_request_otp(req: PhoneRequestModel, request: Request):
    """
    Крок 1: Відправляє OTP-код на номер телефону.

    Якщо номер знайдено у базі — надсилає код через Telegram-бот.
    Якщо номер не знайдено — повідомляє, що потрібна реєстрація (перший вхід).
    """
    redis = _get_redis(request)
    phone = req.phone

    otp = generate_otp()
    await store_otp(redis, phone, otp)

    user = await orm_get_user_by_phone(phone)
    sent_via_bot = False

    if user:
        # Відправляємо OTP через Telegram, якщо бот доступний
        bot = getattr(request.app.state, "bot", None)
        if bot:
            sent_via_bot = await _send_otp_via_bot(bot, user.id, otp)

    if not sent_via_bot:
        # Логуємо OTP для dev/ручного тестування (у production замінити на SMS)
        logger.info("OTP для %s: %s (bot_sent=%s)", phone, otp, sent_via_bot)

    return JSONResponse({
        "success": True,
        "phone": phone,
        "registered": user is not None,
        "sent_via_bot": sent_via_bot,
        "message": (
            "Код надіслано в Telegram-бот" if sent_via_bot
            else "Код згенеровано. Зверніться до адміністратора або введіть код з логів."
        ),
    })


@router.post("/phone/verify")
async def phone_verify_otp(req: PhoneVerifyModel, request: Request):
    """
    Крок 2: Перевіряє OTP та повертає JWT-токени.

    Якщо користувач новий — реєструє його (status='pending').
    """
    redis = _get_redis(request)
    phone = req.phone

    try:
        valid = await verify_otp(redis, phone, req.otp)
    except TooManyAttemptsError:
        raise HTTPException(
            status_code=429,
            detail="Забагато невірних спроб. Спробуйте ще раз через 15 хвилин.",
        )

    if not valid:
        raise HTTPException(status_code=400, detail="Невірний або протермінований код")

    # Шукаємо або створюємо користувача
    user = await orm_get_user_by_phone(phone)

    if not user:
        # Перший вхід — реєструємо нового користувача
        first_name = req.first_name or "Користувач"
        for _ in range(10):
            user_id = 10_000_000_000 + secrets.randbelow(89_999_999_999)
            if not await orm_get_user_by_id(user_id):
                break
        else:
            raise HTTPException(status_code=500, detail="Не вдалося згенерувати унікальний ID")

        user = await orm_create_standalone_user(
            user_id=user_id,
            login=None,
            password_hash=None,
            first_name=first_name,
        )
        await orm_set_user_phone(user.id, phone)
        user = await orm_get_user_by_id(user.id)

    # Генеруємо JWT токени
    login_val = user.login or phone
    access_token = create_token(user.id, login_val, user.role, "access")
    refresh_token = create_token(user.id, login_val, user.role, "refresh")

    return JSONResponse({
        "success": True,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "phone": phone,
            "first_name": user.first_name,
            "role": user.role,
            "status": user.status,
        },
    })
