"""webapp/routers/photos.py

Ендпоінти для керування фото товарів:
- upload (active users)
- list approved photos
- moderation queue + approve/reject (admin/moderator)
- delete any photo (admin/moderator)

RBAC:
- admin: user_id in ADMIN_IDS (env)
- moderator: users.role == 'moderator' AND users.status == 'active'
"""

import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select

from config import ADMIN_IDS
from database.engine import async_session
from database.models import Product, ProductPhoto, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/photos", tags=["photos"])


async def _require_active_user(user_id: int) -> User:
    async with async_session() as session:
        res = await session.execute(select(User).where(User.id == user_id))
        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=403, detail="Користувач не знайдений")
        if user.status != "active":
            raise HTTPException(status_code=403, detail="Доступ не надано")
        return user


async def _require_photo_moderator(user_id: int) -> str:
    """Повертає роль ('admin'|'moderator') або кидає 403."""
    if user_id in ADMIN_IDS:
        return "admin"

    user = await _require_active_user(user_id)
    if user.role not in ("moderator", "admin"):
        raise HTTPException(status_code=403, detail="Недостатньо прав")
    return user.role


@router.post("/upload")
async def upload_photo(
    photo: UploadFile = File(...),
    article: str = Form(...),
    user_id: int = Form(...),
):
    """Завантаження фото товару (тільки active користувачі)."""
    await _require_active_user(user_id)

    if not photo.content_type or not photo.content_type.startswith("image/"):
        return JSONResponse(
            content={"success": False, "message": "Неправильний тип файлу. Оберіть зображення."},
            status_code=400,
        )

    async with async_session() as session:
        prod_result = await session.execute(select(Product).where(Product.артикул == article))
        product = prod_result.scalar_one_or_none()
        if not product:
            return JSONResponse(
                content={"success": False, "message": "Товар не знайдено"},
                status_code=404,
            )

        existing_result = await session.execute(
            select(ProductPhoto).where(
                ProductPhoto.артикул == article,
                ProductPhoto.status.in_(["pending", "approved"]),
            )
        )
        existing = existing_result.scalars().all()
        if len(existing) >= 3:
            return JSONResponse(
                content={"success": False, "message": "Максимум 3 фото на товар"},
                status_code=400,
            )

        # Куди кладемо файл
        webapp_root = Path(__file__).resolve().parent.parent
        uploads_dir = webapp_root / "static" / "uploads" / "photos"
        uploads_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(photo.filename or "photo").suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"

        filename = f"{article}_{uuid.uuid4().hex}{ext}"
        full_path = uploads_dir / filename

        # Пишемо на диск
        with full_path.open("wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)

        file_size = full_path.stat().st_size

        new_photo = ProductPhoto(
            артикул=article,
            file_path=f"uploads/photos/{filename}",
            file_size=file_size,
            original_size=file_size,
            photo_order=len(existing),
            uploaded_by=user_id,
            uploaded_at=datetime.now(),
            status="pending",
        )
        session.add(new_photo)
        await session.commit()

        approved_result = await session.execute(
            select(ProductPhoto)
            .where(ProductPhoto.артикул == article, ProductPhoto.status == "approved")
            .order_by(ProductPhoto.photo_order)
        )
        approved = approved_result.scalars().all()

        return JSONResponse(
            content={
                "success": True,
                "message": "Фото надіслано на модерацію",
                "photos": [p.file_path.split("/")[-1] for p in approved],
            },
            status_code=200,
        )


@router.get("/product/{article}")
async def get_product_photos(article: str):
    """Approved фото для візуалізації."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(ProductPhoto)
                .where(ProductPhoto.артикул == article, ProductPhoto.status == "approved")
                .order_by(ProductPhoto.photo_order)
            )
            photos = result.scalars().all()

            return JSONResponse(
                content={
                    "success": True,
                    "photos": [
                        {"id": p.id, "file_path": p.file_path, "order": p.photo_order}
                        for p in photos
                    ],
                }
            )
    except Exception as e:
        logger.error("❌ ERROR in get_product_photos: %s", e, exc_info=True)
        return JSONResponse(content={"success": False, "photos": []}, status_code=500)


@router.get("/moderation/pending")
async def get_pending_photos(user_id: int):
    """Фото на модерації (admin/moderator)."""
    await _require_photo_moderator(user_id)

    try:
        async with async_session() as session:
            result = await session.execute(
                select(ProductPhoto)
                .where(ProductPhoto.status == "pending")
                .order_by(ProductPhoto.uploaded_at.desc())
            )
            photos = result.scalars().all()

            result_list = []
            for p in photos:
                prod_res = await session.execute(select(Product).where(Product.артикул == p.артикул))
                product = prod_res.scalar_one_or_none()

                user_res = await session.execute(select(User).where(User.id == p.uploaded_by))
                uploader = user_res.scalar_one_or_none()

                uploader_name = ""
                if uploader:
                    uploader_name = uploader.first_name
                    if uploader.username:
                        uploader_name += f" (@{uploader.username})"

                result_list.append(
                    {
                        "id": p.id,
                        "article": p.артикул,
                        "product_name": product.назва if product else "",
                        "file_path": p.file_path,
                        "file_size": p.file_size,
                        "original_size": p.original_size,
                        "uploaded_by": uploader_name or f"ID {p.uploaded_by}",
                        "uploaded_at": p.uploaded_at.strftime("%d.%m.%Y %H:%M"),
                    }
                )

            return JSONResponse(content={"success": True, "photos": result_list})
    except Exception as e:
        logger.error("❌ ERROR in get_pending_photos: %s", e, exc_info=True)
        return JSONResponse(content={"success": False, "photos": []}, status_code=500)


@router.post("/moderation/{photo_id}")
async def moderate_photo(
    photo_id: int,
    status: str = Form(...),
    reason: str = Form(None),
    user_id: int = Form(...),
):
    """Модерація: схвалити або відхилити (admin/moderator)."""
    await _require_photo_moderator(user_id)

    if status not in ("approved", "rejected"):
        return JSONResponse(
            content={"success": False, "message": "Некоректний статус"},
            status_code=400,
        )

    try:
        async with async_session() as session:
            result = await session.execute(select(ProductPhoto).where(ProductPhoto.id == photo_id))
            photo = result.scalar_one_or_none()

            if not photo:
                raise HTTPException(status_code=404, detail="Photo not found")

            photo.status = status
            photo.moderated_by = user_id
            photo.moderated_at = datetime.now()

            if status == "rejected":
                photo.rejection_reason = reason
            else:
                photo.rejection_reason = None

            await session.commit()

            return JSONResponse(
                content={
                    "success": True,
                    "message": "Фото схвалено" if status == "approved" else "Фото відхилено",
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ ERROR in moderate_photo: %s", e, exc_info=True)
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)


@router.delete("/{photo_id}")
async def delete_photo(photo_id: int, user_id: int):
    """Видалення фото (тільки admin/moderator)."""
    await _require_photo_moderator(user_id)

    try:
        async with async_session() as session:
            result = await session.execute(select(ProductPhoto).where(ProductPhoto.id == photo_id))
            photo = result.scalar_one_or_none()

            if not photo:
                raise HTTPException(status_code=404, detail="Photo not found")

            # Видаляємо фізичний файл
            webapp_root = Path(__file__).resolve().parent.parent
            full_file_path = webapp_root / "static" / photo.file_path
            if full_file_path.exists():
                full_file_path.unlink()

            await session.delete(photo)
            await session.commit()

            return JSONResponse(content={"success": True, "message": "Фото видалено"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ ERROR in delete_photo: %s", e, exc_info=True)
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
