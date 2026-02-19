"""Product business logic service."""

from typing import List, Optional
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Product
from schemas.product import ProductCreate, ProductUpdate, ProductResponse
from services.base import BaseService


class ProductService(BaseService[Product]):
    """Service for product-related business logic."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def search(
        self, query: str, limit: int = 50, user_current_department: Optional[str] = None
    ) -> List[ProductResponse]:
        """
        Search products by article or name.
        
        Args:
            query: Search query
            limit: Maximum results
            user_current_department: User's current department (for locking logic)
            
        Returns:
            List of ProductResponse with is_different_department flag
        """
        # Build search query
        stmt = (
            select(Product)
            .where(Product.is_active == True)
            .where(
                or_(
                    Product.article.ilike(f"%{query}%"),
                    Product.name.ilike(f"%{query}%"),
                )
            )
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        products = result.scalars().all()

        # Convert to response DTOs
        responses = []
        for product in products:
            response = ProductResponse.from_orm(product)
            
            # Set department locking flag
            if user_current_department and product.department != user_current_department:
                response.is_different_department = True
            
            responses.append(response)

        return responses

    async def get_by_id(self, product_id: int) -> Optional[ProductResponse]:
        """Get product by ID."""
        stmt = select(Product).where(Product.id == product_id)
        result = await self.session.execute(stmt)
        product = result.scalar_one_or_none()

        return ProductResponse.from_orm(product) if product else None

    async def get_by_article(self, article: str) -> Optional[ProductResponse]:
        """Get product by article."""
        stmt = select(Product).where(Product.article == article)
        result = await self.session.execute(stmt)
        product = result.scalar_one_or_none()

        return ProductResponse.from_orm(product) if product else None

    async def create(self, data: ProductCreate) -> ProductResponse:
        """Create new product."""
        product = Product(**data.dict())
        self.session.add(product)
        await self.commit()
        await self.refresh(product)

        return ProductResponse.from_orm(product)

    async def update(self, product_id: int, data: ProductUpdate) -> Optional[ProductResponse]:
        """Update product."""
        stmt = select(Product).where(Product.id == product_id)
        result = await self.session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            return None

        # Update only provided fields
        for field, value in data.dict(exclude_unset=True).items():
            setattr(product, field, value)

        await self.commit()
        await self.refresh(product)

        return ProductResponse.from_orm(product)

    async def reserve(self, product_id: int, quantity: int) -> bool:
        """
        Reserve product quantity.
        
        Returns:
            True if reserved successfully, False if not enough available
        """
        stmt = select(Product).where(Product.id == product_id).with_for_update()
        result = await self.session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            return False

        # Check availability
        if product.available - product.reserved < quantity:
            return False

        product.reserved += quantity
        await self.commit()

        return True

    async def release_reservation(self, product_id: int, quantity: int) -> bool:
        """Release reserved quantity."""
        stmt = select(Product).where(Product.id == product_id).with_for_update()
        result = await self.session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            return False

        product.reserved = max(0, product.reserved - quantity)
        await self.commit()

        return True

    async def get_stats(self) -> dict:
        """Get product statistics."""
        # Total products
        total_stmt = select(func.count(Product.id))
        total_result = await self.session.execute(total_stmt)
        total = total_result.scalar()

        # Active products
        active_stmt = select(func.count(Product.id)).where(Product.is_active == True)
        active_result = await self.session.execute(active_stmt)
        active = active_result.scalar()

        # Total available and reserved
        sum_stmt = select(
            func.sum(Product.available), func.sum(Product.reserved)
        ).where(Product.is_active == True)
        sum_result = await self.session.execute(sum_stmt)
        available, reserved = sum_result.one()

        return {
            "total_products": total or 0,
            "active_products": active or 0,
            "inactive_products": (total or 0) - (active or 0),
            "total_available": int(available or 0),
            "total_reserved": int(reserved or 0),
        }
