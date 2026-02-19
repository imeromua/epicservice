"""User repository for data access."""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, SavedList
from repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User entity."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_or_create(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> tuple[User, bool]:
        """
        Get existing user or create new one.
        
        Returns:
            (User, created) tuple where created is True if user was created
        """
        existing = await self.get_by_id(user_id)
        if existing:
            # Update user info if changed
            if username and existing.username != username:
                existing.username = username
            if first_name and existing.first_name != first_name:
                existing.first_name = first_name
            if last_name and existing.last_name != last_name:
                existing.last_name = last_name

            await self.session.flush()
            return existing, False

        # Create new
        user = await self.create(
            id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        return user, True

    async def get_all_active(self, days: int = 30) -> List[User]:
        """
        Get users active in last N days.
        
        Active = users who created saved lists
        """
        since_date = datetime.utcnow() - timedelta(days=days)

        stmt = (
            select(User)
            .join(SavedList, SavedList.user_id == User.id)
            .where(SavedList.created_at >= since_date)
            .distinct()
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_total_count(self) -> int:
        """Get total users count."""
        stmt = select(func.count(User.id))
        result = await self.session.execute(stmt)
        return result.scalar()
