"""List-related schemas."""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator


class TempListItem(BaseModel):
    """Schema for item in temporary list."""

    product_id: int = Field(..., gt=0, description="Product ID")
    quantity: int = Field(..., gt=0, description="Quantity to order")

    # Additional product info (for display)
    article: Optional[str] = None
    name: Optional[str] = None
    department: Optional[str] = None
    price: Optional[float] = None
    available: Optional[int] = None

    @validator("quantity")
    def validate_quantity(cls, v):
        """Quantity must be positive."""
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "product_id": 1,
                "quantity": 5,
                "article": "12345",
                "name": "Test Product",
                "department": "ДСК",
                "price": 100.50,
                "available": 10,
            }
        }


class TempListResponse(BaseModel):
    """Schema for temporary list response."""

    user_id: int = Field(..., description="User Telegram ID")
    items: List[TempListItem] = Field(..., description="List items")
    total_items: int = Field(..., ge=0, description="Total number of items")
    total_price: float = Field(..., ge=0, description="Total price of all items")
    current_department: Optional[str] = Field(None, description="Current locked department")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 123456789,
                "items": [
                    {
                        "product_id": 1,
                        "quantity": 5,
                        "article": "12345",
                        "name": "Test Product",
                        "department": "ДСК",
                        "price": 100.50,
                        "available": 10,
                    }
                ],
                "total_items": 1,
                "total_price": 502.50,
                "current_department": "ДСК",
            }
        }


class SavedListResponse(BaseModel):
    """Schema for saved list response."""

    id: int = Field(..., description="Saved list ID")
    user_id: int = Field(..., description="User Telegram ID")
    filename: str = Field(..., description="Excel filename")
    filepath: str = Field(..., description="File path")
    created_at: datetime = Field(..., description="Creation timestamp")
    total_items: Optional[int] = Field(None, description="Number of items")
    total_price: Optional[float] = Field(None, description="Total price")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 123456789,
                "filename": "123456789_20260219_190000.xlsx",
                "filepath": "archives/active/123456789/123456789_20260219_190000.xlsx",
                "created_at": "2026-02-19T19:00:00",
                "total_items": 5,
                "total_price": 1250.00,
            }
        }


class ListStatsResponse(BaseModel):
    """Schema for list statistics."""

    total_lists: int = Field(..., ge=0, description="Total saved lists")
    total_amount: float = Field(..., ge=0, description="Total amount spent")
    this_month: int = Field(..., ge=0, description="Lists this month")
    popular_department: Optional[str] = Field(None, description="Most used department")
    avg_list_price: float = Field(..., ge=0, description="Average list price")

    class Config:
        json_schema_extra = {
            "example": {
                "total_lists": 42,
                "total_amount": 52500.00,
                "this_month": 8,
                "popular_department": "ДСК",
                "avg_list_price": 1250.00,
            }
        }
