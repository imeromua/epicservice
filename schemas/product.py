"""Product-related schemas."""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator


class ProductBase(BaseModel):
    """Base product schema with common fields."""

    article: str = Field(..., min_length=1, max_length=50, description="Product article")
    name: str = Field(..., min_length=1, max_length=500, description="Product name")
    department: str = Field(..., min_length=1, max_length=100, description="Department name")
    group_name: Optional[str] = Field(None, max_length=200, description="Product group")
    price: float = Field(..., gt=0, description="Product price")
    available: int = Field(..., ge=0, description="Available quantity")

    @validator("price")
    def validate_price(cls, v):
        """Ensure price has max 2 decimal places."""
        if round(v, 2) != v:
            raise ValueError("Price must have at most 2 decimal places")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "article": "12345",
                "name": "Test Product",
                "department": "ДСК",
                "group_name": "Group A",
                "price": 100.50,
                "available": 10,
            }
        }


class ProductCreate(ProductBase):
    """Schema for creating a new product."""

    no_movement: int = Field(0, ge=0, description="Days without movement")
    is_active: bool = Field(True, description="Product active status")


class ProductUpdate(BaseModel):
    """Schema for updating product (all fields optional)."""

    article: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    group_name: Optional[str] = Field(None, max_length=200)
    price: Optional[float] = Field(None, gt=0)
    available: Optional[int] = Field(None, ge=0)
    reserved: Optional[int] = Field(None, ge=0)
    no_movement: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    """Schema for product response (what API returns)."""

    id: int = Field(..., description="Product ID")
    reserved: int = Field(0, ge=0, description="Reserved quantity")
    no_movement: int = Field(0, ge=0, description="Days without movement")
    is_active: bool = Field(True, description="Product active status")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # Computed fields
    is_different_department: bool = Field(
        False, description="True if product from different department"
    )
    actual_available: int = Field(
        ..., description="Actual available (available - reserved)"
    )

    @validator("actual_available", pre=True, always=True)
    def calculate_actual_available(cls, v, values):
        """Calculate actual available quantity."""
        if v is None:
            return values.get("available", 0) - values.get("reserved", 0)
        return v

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "article": "12345",
                "name": "Test Product",
                "department": "ДСК",
                "group_name": "Group A",
                "price": 100.50,
                "available": 10,
                "reserved": 2,
                "no_movement": 0,
                "is_active": True,
                "updated_at": "2026-02-19T19:00:00",
                "is_different_department": False,
                "actual_available": 8,
            }
        }


class ProductSearchResponse(BaseModel):
    """Schema for product search response."""

    products: List[ProductResponse] = Field(..., description="List of found products")
    total: int = Field(..., ge=0, description="Total products found")
    query: str = Field(..., description="Search query used")

    class Config:
        json_schema_extra = {
            "example": {
                "products": [
                    {
                        "id": 1,
                        "article": "12345",
                        "name": "Test Product",
                        "department": "ДСК",
                        "group_name": "Group A",
                        "price": 100.50,
                        "available": 10,
                        "reserved": 2,
                        "no_movement": 0,
                        "is_active": True,
                        "updated_at": "2026-02-19T19:00:00",
                        "is_different_department": False,
                        "actual_available": 8,
                    }
                ],
                "total": 1,
                "query": "12345",
            }
        }
