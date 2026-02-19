"""List management business logic service."""

from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import TempList, Product, User
from schemas.list import TempListItem, TempListResponse
from services.base import BaseService
from services.product_service import ProductService


class ListService(BaseService[TempList]):
    """Service for list-related business logic."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.product_service = ProductService(session)

    async def get_current_department(self, user_id: int) -> Optional[str]:
        """
        Get current locked department for user.
        
        Returns:
            Department name if user has list, None otherwise
        """
        stmt = (
            select(Product.department)
            .join(TempList, TempList.product_id == Product.id)
            .where(TempList.user_id == user_id)
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_list(self, user_id: int) -> TempListResponse:
        """
        Get user's current temporary list.
        
        Returns:
            TempListResponse with items and totals
        """
        stmt = (
            select(TempList, Product)
            .join(Product, TempList.product_id == Product.id)
            .where(TempList.user_id == user_id)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        items = []
        total_price = 0.0
        current_department = None

        for temp_item, product in rows:
            if not current_department:
                current_department = product.department

            item = TempListItem(
                product_id=product.id,
                quantity=temp_item.quantity,
                article=product.article,
                name=product.name,
                department=product.department,
                price=product.price,
                available=product.available,
            )
            items.append(item)
            total_price += product.price * temp_item.quantity

        return TempListResponse(
            user_id=user_id,
            items=items,
            total_items=len(items),
            total_price=round(total_price, 2),
            current_department=current_department,
        )

    async def add_product(
        self, user_id: int, product_id: int, quantity: int
    ) -> TempListResponse:
        """
        Add product to user's list.
        
        Raises:
            ValueError: If department is different or product unavailable
        """
        # Check if product exists
        product_response = await self.product_service.get_by_id(product_id)
        if not product_response:
            raise ValueError("Product not found")

        # Check department locking
        current_dept = await self.get_current_department(user_id)
        if current_dept and current_dept != product_response.department:
            raise ValueError(
                f"Cannot add product from {product_response.department}. "
                f"Current list is from {current_dept}. Save list first."
            )

        # Check availability
        if product_response.actual_available < quantity:
            raise ValueError(
                f"Only {product_response.actual_available} available (requested {quantity})"
            )

        # Check if already in list
        check_stmt = select(TempList).where(
            TempList.user_id == user_id, TempList.product_id == product_id
        )
        check_result = await self.session.execute(check_stmt)
        existing = check_result.scalar_one_or_none()

        if existing:
            # Update quantity
            existing.quantity += quantity
        else:
            # Add new
            temp_item = TempList(
                user_id=user_id, product_id=product_id, quantity=quantity
            )
            self.session.add(temp_item)

        # Reserve products
        reserved = await self.product_service.reserve(product_id, quantity)
        if not reserved:
            await self.rollback()
            raise ValueError("Failed to reserve product")

        await self.commit()

        return await self.get_list(user_id)

    async def update_quantity(
        self, user_id: int, product_id: int, new_quantity: int
    ) -> TempListResponse:
        """
        Update product quantity in list.
        
        Raises:
            ValueError: If product not in list or invalid quantity
        """
        if new_quantity < 0:
            raise ValueError("Quantity cannot be negative")

        stmt = select(TempList).where(
            TempList.user_id == user_id, TempList.product_id == product_id
        )
        result = await self.session.execute(stmt)
        temp_item = result.scalar_one_or_none()

        if not temp_item:
            raise ValueError("Product not in list")

        old_quantity = temp_item.quantity
        delta = new_quantity - old_quantity

        if new_quantity == 0:
            # Remove from list
            await self.session.delete(temp_item)
            await self.product_service.release_reservation(product_id, old_quantity)
        else:
            # Update quantity
            temp_item.quantity = new_quantity

            if delta > 0:
                # Reserve more
                reserved = await self.product_service.reserve(product_id, delta)
                if not reserved:
                    await self.rollback()
                    raise ValueError("Not enough available")
            elif delta < 0:
                # Release some
                await self.product_service.release_reservation(product_id, abs(delta))

        await self.commit()

        return await self.get_list(user_id)

    async def clear_list(self, user_id: int) -> None:
        """
        Clear user's temporary list and release all reservations.
        """
        # Get list to release reservations
        list_response = await self.get_list(user_id)

        for item in list_response.items:
            await self.product_service.release_reservation(
                item.product_id, item.quantity
            )

        # Delete all items
        stmt = delete(TempList).where(TempList.user_id == user_id)
        await self.session.execute(stmt)
        await self.commit()
