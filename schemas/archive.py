"""Archive-related schemas."""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ArchiveItem(BaseModel):
    """Schema for single archive item."""

    filename: str = Field(..., description="Archive filename")
    created_at: datetime = Field(..., description="Creation timestamp")
    size_bytes: Optional[int] = Field(None, ge=0, description="File size in bytes")
    department: Optional[str] = Field(None, description="Department")
    total_items: Optional[int] = Field(None, ge=0, description="Number of items")
    total_price: Optional[float] = Field(None, ge=0, description="Total price")
    author_id: Optional[int] = Field(None, description="Author user ID")

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "123456789_20260219_190000.xlsx",
                "created_at": "2026-02-19T19:00:00",
                "size_bytes": 15360,
                "department": "ДСК",
                "total_items": 5,
                "total_price": 1250.00,
                "author_id": 123456789,
            }
        }


class ArchiveStatsResponse(BaseModel):
    """Schema for archive file statistics."""

    filename: str = Field(..., description="Archive filename")
    department: str = Field(..., description="Department")
    total_items: int = Field(..., ge=0, description="Total items")
    total_price: float = Field(..., ge=0, description="Total price")
    created_at: datetime = Field(..., description="Creation timestamp")
    products: Optional[List[dict]] = Field(None, description="List of products")

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "123456789_20260219_190000.xlsx",
                "department": "ДСК",
                "total_items": 5,
                "total_price": 1250.00,
                "created_at": "2026-02-19T19:00:00",
                "products": [
                    {
                        "article": "12345",
                        "name": "Test Product",
                        "quantity": 5,
                        "price": 100.50,
                        "total": 502.50,
                    }
                ],
            }
        }


class ArchiveListResponse(BaseModel):
    """Schema for list of archives."""

    archives: List[ArchiveItem] = Field(..., description="List of archives")
    total: int = Field(..., ge=0, description="Total archives count")
    user_id: Optional[int] = Field(None, description="User ID (if filtered)")

    class Config:
        json_schema_extra = {
            "example": {
                "archives": [
                    {
                        "filename": "123456789_20260219_190000.xlsx",
                        "created_at": "2026-02-19T19:00:00",
                        "size_bytes": 15360,
                        "department": "ДСК",
                        "total_items": 5,
                        "total_price": 1250.00,
                        "author_id": 123456789,
                    }
                ],
                "total": 1,
                "user_id": 123456789,
            }
        }
