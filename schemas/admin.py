"""Admin-related schemas."""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class AdminStatsResponse(BaseModel):
    """Schema for admin statistics dashboard."""

    total_users: int = Field(..., ge=0, description="Total registered users")
    active_lists: int = Field(..., ge=0, description="Users with unsaved lists")
    total_products: int = Field(..., ge=0, description="Total products in catalog")
    active_products: int = Field(..., ge=0, description="Active products")
    total_reserved: float = Field(..., ge=0, description="Total reserved amount")
    departments: Dict[str, int] = Field(..., description="Products by department")
    reserved_by_department: Dict[str, float] = Field(
        ..., description="Reserved amounts by department"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total_users": 150,
                "active_lists": 12,
                "total_products": 5000,
                "active_products": 4850,
                "total_reserved": 25000.00,
                "departments": {"ДСК": 2000, "ОЛ": 1500, "МОТО": 1350},
                "reserved_by_department": {
                    "ДСК": 15000.00,
                    "ОЛ": 7000.00,
                    "МОТО": 3000.00,
                },
            }
        }


class UserInfoResponse(BaseModel):
    """Schema for user information."""

    id: int = Field(..., description="User Telegram ID")
    username: Optional[str] = Field(None, description="Telegram username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    created_at: str = Field(..., description="Registration date")
    has_active_list: bool = Field(..., description="Has unsaved list")
    total_saved_lists: Optional[int] = Field(None, description="Total saved lists count")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 123456789,
                "username": "testuser",
                "first_name": "Test",
                "last_name": "User",
                "created_at": "2026-01-15 10:30:00",
                "has_active_list": True,
                "total_saved_lists": 15,
            }
        }


class ProductInfoResponse(BaseModel):
    """Schema for product information summary."""

    total_products: int = Field(..., ge=0)
    active_products: int = Field(..., ge=0)
    inactive_products: int = Field(..., ge=0)
    total_available: int = Field(..., ge=0)
    total_reserved: int = Field(..., ge=0)
    departments: List[str] = Field(...)
    groups: List[str] = Field(...)

    class Config:
        json_schema_extra = {
            "example": {
                "total_products": 5000,
                "active_products": 4850,
                "inactive_products": 150,
                "total_available": 125000,
                "total_reserved": 5000,
                "departments": ["ДСК", "ОЛ", "МОТО"],
                "groups": ["Group A", "Group B", "Group C"],
            }
        }


class BroadcastRequest(BaseModel):
    """Schema for broadcast message request."""

    user_id: int = Field(..., description="Admin user ID")
    message: str = Field(..., min_length=1, max_length=4096, description="Message text")
    target_users: Optional[List[int]] = Field(
        None, description="Specific user IDs (if None, send to all)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 111111111,
                "message": "🔔 Увага! Оновлення каталогу о 15:00",
                "target_users": None,
            }
        }
