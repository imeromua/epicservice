"""Base service class."""

from typing import TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseService(Generic[T]):
    """Base service with common functionality."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session."""
        self.session = session

    async def commit(self):
        """Commit transaction."""
        await self.session.commit()

    async def rollback(self):
        """Rollback transaction."""
        await self.session.rollback()

    async def refresh(self, instance: T) -> T:
        """Refresh instance from database."""
        await self.session.refresh(instance)
        return instance
