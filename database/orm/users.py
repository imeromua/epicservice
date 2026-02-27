# epicservice/database/orm/users.py

import logging
from typing import List

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from database.engine import async_session, sync_session
from database.models import User

logger = logging.getLogger(__name__)


async def orm_upsert_user(
    user_id: int,
    username: str | None,
    first_name: str,
):
    """
    Додає нового користувача або оновлює дані існуючого.

    ВАЖЛИВО:
    - При першому створенні: status='pending', role='user'
    - При повторному /start: НЕ перетирає status/role/audit, оновлює тільки username/first_name (+ updated_at)
    """
    async with async_session() as session:
        stmt = insert(User).values(
            id=user_id,
            username=username,
            first_name=first_name,
            status="pending",
            role="user",
            updated_at=func.now(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "username": username,
                "first_name": first_name,
                "updated_at": func.now(),
            },
        )
        await session.execute(stmt)
        await session.commit()


async def orm_get_user_by_id(user_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


async def orm_set_user_status(
    target_user_id: int,
    status: str,
    actor_user_id: int | None = None,
    reason: str | None = None,
) -> None:
    values: dict = {"status": status, "updated_at": func.now()}

    if status == "active":
        # unblock/activate
        values.update(
            {
                "blocked_by": None,
                "blocked_at": None,
                "blocked_reason": None,
            }
        )

    if status == "blocked":
        values.update(
            {
                "blocked_by": actor_user_id,
                "blocked_at": func.now(),
                "blocked_reason": reason,
            }
        )

    async with async_session() as session:
        await session.execute(update(User).where(User.id == target_user_id).values(**values))
        await session.commit()


async def orm_approve_user(target_user_id: int, admin_user_id: int) -> None:
    async with async_session() as session:
        await session.execute(
            update(User)
            .where(User.id == target_user_id)
            .values(
                status="active",
                approved_by=admin_user_id,
                approved_at=func.now(),
                updated_at=func.now(),
                # На всяк випадок, якщо юзер був блокований раніше
                blocked_by=None,
                blocked_at=None,
                blocked_reason=None,
            )
        )
        await session.commit()


async def orm_block_user(target_user_id: int, admin_user_id: int, reason: str | None) -> None:
    await orm_set_user_status(
        target_user_id=target_user_id,
        status="blocked",
        actor_user_id=admin_user_id,
        reason=reason,
    )


async def orm_unblock_user(target_user_id: int, admin_user_id: int | None = None) -> None:
    # admin_user_id поки не зберігаємо окремо для unblock, але можемо додати при потребі
    await orm_set_user_status(
        target_user_id=target_user_id,
        status="active",
        actor_user_id=admin_user_id,
        reason=None,
    )


async def orm_set_user_role(target_user_id: int, role: str) -> None:
    async with async_session() as session:
        await session.execute(
            update(User)
            .where(User.id == target_user_id)
            .values(role=role, updated_at=func.now())
        )
        await session.commit()


async def orm_list_users(
    status: str | None = None,
    role: str | None = None,
    q: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[User], int]:
    """Повертає список користувачів і total для пагінації."""
    async with async_session() as session:
        base = select(User)
        count_q = select(func.count()).select_from(User)

        if status:
            base = base.where(User.status == status)
            count_q = count_q.where(User.status == status)
        if role:
            base = base.where(User.role == role)
            count_q = count_q.where(User.role == role)
        if q:
            like = f"%{q}%"
            base = base.where((User.first_name.ilike(like)) | (User.username.ilike(like)))
            count_q = count_q.where((User.first_name.ilike(like)) | (User.username.ilike(like)))

        total = (await session.execute(count_q)).scalar_one()
        users = (await session.execute(base.order_by(User.created_at.desc()).offset(offset).limit(limit))).scalars().all()
        return list(users), int(total)


def orm_get_all_users_sync() -> List[int]:
    """
    Синхронно отримує ID всіх зареєстрованих користувачів для розсилки.

    Returns:
        Список всіх унікальних user_id з таблиці users.
    """
    with sync_session() as session:
        query = select(User.id)
        return list(session.execute(query).scalars().all())


async def orm_get_user_by_login(login: str) -> User | None:
    """Знаходить користувача за логіном (для автономної автентифікації)."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.login == login))
        return result.scalar_one_or_none()


async def orm_get_user_by_phone(phone: str) -> User | None:
    """Знаходить користувача за номером телефону."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()


async def orm_set_user_phone(user_id: int, phone: str) -> None:
    """Зберігає номер телефону користувача."""
    async with async_session() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(phone=phone, updated_at=func.now())
        )
        await session.commit()


async def orm_create_standalone_user(
    user_id: int,
    login: str,
    password_hash: str,
    first_name: str,
) -> User:
    """Створює користувача з логіном та паролем (автономний режим)."""
    async with async_session() as session:
        user = User(
            id=user_id,
            login=login,
            password_hash=password_hash,
            first_name=first_name,
            status="pending",
            role="user",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
