"""List repository for data access."""

from typing import List, Optional, Tuple
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import TempList, Product, SavedList, SavedListItem
from repositories.base import BaseRepository


class ListRepository(BaseRepository[TempList]):
    """Repository for TempList entity."""

    def __init__(self, session: AsyncSession):
        super().__init__(TempList, session)

    async def get_user_list(self, user_id: int) -> List[Tuple[TempList, Product]]:
        """
        Get user's temp list with product details.
        
        Returns:
            List of (TempList, Product) tuples
        """
        stmt = (
            select(TempList, Product)
            .join(Product, TempList.product_id == Product.id)
            .where(TempList.user_id == user_id)
        )

        result = await self.session.execute(stmt)
        return list(result.all())

    async def get_user_item(
        self, user_id: int, product_id: int
    ) -> Optional[TempList]:
        """Get specific item from user's list."""
        stmt = select(TempList).where(
            TempList.user_id == user_id,
            TempList.product_id == product_id,
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_or_update_item(
        self, user_id: int, product_id: int, quantity: int
    ) -> TempList:
        """Add item or update quantity if exists."""
        existing = await self.get_user_item(user_id, product_id)

        if existing:
            existing.quantity += quantity
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        else:
            return await self.create(
                user_id=user_id,
                product_id=product_id,
                quantity=quantity,
            )

    async def update_item_quantity(
        self, user_id: int, product_id: int, new_quantity: int
    ) -> bool:
        """Update item quantity."""
        item = await self.get_user_item(user_id, product_id)
        if not item:
            return False

        item.quantity = new_quantity
        await self.session.flush()
        return True

    async def remove_item(self, user_id: int, product_id: int) -> bool:
        """Remove item from list."""
        stmt = delete(TempList).where(
            TempList.user_id == user_id,
            TempList.product_id == product_id,
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        return result.rowcount > 0

    async def clear_user_list(self, user_id: int) -> int:
        """
        Clear all items from user's list.
        
        Returns:
            Number of deleted items
        """
        stmt = delete(TempList).where(TempList.user_id == user_id)
        result = await self.session.execute(stmt)
        await self.session.flush()

        return result.rowcount

    async def get_current_department(self, user_id: int) -> Optional[str]:
        """Get current department from user's list."""
        stmt = (
            select(Product.department)
            .join(TempList, TempList.product_id == Product.id)
            .where(TempList.user_id == user_id)
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_list(
        self, user_id: int, filename: str, filepath: str
    ) -> SavedList:
        """Save current list to archives."""
        # Get current list
        items = await self.get_user_list(user_id)

        # Create SavedList
        saved_list = SavedList(
            user_id=user_id,
            filename=filename,
            filepath=filepath,
        )
        self.session.add(saved_list)
        await self.session.flush()
        await self.session.refresh(saved_list)

        # Create SavedListItems
        for temp_item, product in items:
            saved_item = SavedListItem(
                saved_list_id=saved_list.id,
                product_id=product.id,
                quantity=temp_item.quantity,
                price=product.price,
            )
            self.session.add(saved_item)

        await self.session.flush()

        return saved_list
