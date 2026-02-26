"""
Роутер автентифікації для автономного додатку.
JWT-based login/password auth without Telegram dependency.
"""

import logging
import random
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import JWT_SECRET_KEY
from database.orm.users import orm_create_standalone_user, orm_get_user_by_id, orm_get_user_by_login

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
        user_id = random.randint(10_000_000_000, 99_999_999_999)
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
