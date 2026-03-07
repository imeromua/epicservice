# webapp/routers/user_management.py

"""Ендпоінти керування користувачами.

Маршрути:
- /api/admin/user-management/users
- /api/admin/user-management/approve
- /api/admin/user-management/block
- /api/admin/user-management/unblock
- /api/admin/user-management/role

Доступ: тільки admin (JWT Bearer токен).
Адмін перевіряється за ADMIN_IDS з .env — client-supplied user_id більше не приймається
як авторитетне джерело ідентичності на цих ендпоінтах.
"""

import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import BOT_TOKEN, WEBAPP_URL
from database.orm import (
    orm_approve_user,
    orm_block_user,
    orm_get_user_by_id,
    orm_list_users,
    orm_set_user_role,
    orm_unblock_user,
)
from webapp.deps import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user-management")
bot = Bot(token=BOT_TOKEN)


class ApproveRequest(BaseModel):
    target_user_id: int


class BlockRequest(BaseModel):
    target_user_id: int
    reason: str | None = None


class UnblockRequest(BaseModel):
    target_user_id: int


class RoleRequest(BaseModel):
    target_user_id: int
    role: str


@router.get("/users")
async def list_users(
    admin_user_id: int = Depends(require_admin),
    status: str | None = Query(None),
    role: str | None = Query(None),
    q: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    users, total = await orm_list_users(status=status, role=role, q=q, offset=offset, limit=limit)

    def display_name(u) -> str:
        base = (u.first_name or "").strip() or f"ID {u.id}"
        if u.username:
            return f"{base} (@{u.username})"
        return base

    return JSONResponse(
        content={
            "success": True,
            "total": total,
            "users": [
                {
                    "id": u.id,
                    "username": u.username,
                    "first_name": u.first_name,
                    "status": u.status,
                    "role": u.role,
                    "display_name": display_name(u),
                }
                for u in users
            ],
        }
    )


@router.post("/approve")
async def approve_user(req: ApproveRequest, admin_user_id: int = Depends(require_admin)):
    target = await orm_get_user_by_id(req.target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    await orm_approve_user(req.target_user_id, admin_user_id)

    # Нотифікація в Telegram з WebApp кнопкою
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌐 Відкрити EpicService",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ]
    )

    try:
        await bot.send_message(
            req.target_user_id,
            "✅ Ваш доступ підтверджено адміністратором.\nНатисніть кнопку нижче, щоб відкрити EpicService.",
            reply_markup=kb,
        )
    except Exception as e:
        logger.warning("Failed to notify approved user %s: %s", req.target_user_id, e)

    return JSONResponse(content={"success": True, "message": "Користувача підтверджено"})


@router.post("/block")
async def block_user(req: BlockRequest, admin_user_id: int = Depends(require_admin)):
    target = await orm_get_user_by_id(req.target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    await orm_block_user(req.target_user_id, admin_user_id, req.reason)
    return JSONResponse(content={"success": True, "message": "Користувача заблоковано"})


@router.post("/unblock")
async def unblock_user(req: UnblockRequest, admin_user_id: int = Depends(require_admin)):
    target = await orm_get_user_by_id(req.target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    await orm_unblock_user(req.target_user_id, admin_user_id)
    return JSONResponse(content={"success": True, "message": "Користувача розблоковано"})


@router.post("/role")
async def set_role(req: RoleRequest, admin_user_id: int = Depends(require_admin)):
    if req.role not in ("user", "moderator", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")

    target = await orm_get_user_by_id(req.target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    await orm_set_user_role(req.target_user_id, req.role)
    return JSONResponse(content={"success": True, "message": "Роль змінено"})

