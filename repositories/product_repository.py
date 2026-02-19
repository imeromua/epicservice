"""Product repository for data access."""

from typing import List, Optional
from sqlalchemy import select, func, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Product
from repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    """Repository for Product entity."""

    def __init__(self, session: AsyncSession):
        super().__init__(Product, session)

    async def search_by_query(
        self, query: str, limit: int = 50, only_active: bool = True
    ) -> List[Product]:
        """Search products by article or name."""
        stmt = select(Product).where(
            or_(
                Product.article.ilike(f"%{query}%"),
                Product.name.ilike(f"%{query}%"),
            )
        )

        if only_active:
            stmt = stmt.where(Product.is_active == True)

        stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_article(self, article: str) -> Optional[Product]:
        """Get product by article."""
        stmt = select(Product).where(Product.article == article)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_count(self) -> int:
        """Get count of active products."""
        stmt = select(func.count(Product.id)).where(Product.is_active == True)
        result = await self.session.execute(stmt)
        return result.scalar()

    async def get_by_department(self, department: str, only_active: bool = True) -> List[Product]:
        """Get products by department."""
        stmt = select(Product).where(Product.department == department)

        if only_active:
            stmt = stmt.where(Product.is_active == True)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def reserve_quantity(self, product_id: int, quantity: int) -> bool:
        """
        Reserve product quantity (with lock).
        
        Returns:
            True if reserved, False if not enough available
        """
        # Get with FOR UPDATE lock
        stmt = select(Product).where(Product.id == product_id).with_for_update()
        result = await self.session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            return False

        # Check availability
        if product.available - product.reserved < quantity:
            return False

        # Update reserved
        product.reserved += quantity
        await self.session.flush()

        return True

    async def release_quantity(self, product_id: int, quantity: int) -> bool:
        """Release reserved quantity."""
        stmt = select(Product).where(Product.id == product_id).with_for_update()
        result = await self.session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            return False

        product.reserved = max(0, product.reserved - quantity)
        await self.session.flush()

        return True

    async def bulk_deactivate(self, exclude_articles: List[str]) -> int:
        """
        Deactivate products not in the list (for import).
        
        Returns:
            Number of deactivated products
        """
        stmt = (
            update(Product)
            .where(Product.article.notin_(exclude_articles))
            .where(Product.is_active == True)
            .values(is_active=False)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        return result.rowcount
