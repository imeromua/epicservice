"""Pydantic schemas for API contracts."""

from schemas.product import (
    ProductBase,
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductSearchResponse,
)
from schemas.list import (
    TempListItem,
    TempListResponse,
    SavedListResponse,
    ListStatsResponse,
)
from schemas.archive import (
    ArchiveItem,
    ArchiveStatsResponse,
    ArchiveListResponse,
)
from schemas.admin import (
    AdminStatsResponse,
    UserInfoResponse,
    ProductInfoResponse,
    BroadcastRequest,
)
from schemas.common import (
    HealthResponse,
    MessageResponse,
    ErrorResponse,
)

__all__ = [
    # Product
    "ProductBase",
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "ProductSearchResponse",
    # List
    "TempListItem",
    "TempListResponse",
    "SavedListResponse",
    "ListStatsResponse",
    # Archive
    "ArchiveItem",
    "ArchiveStatsResponse",
    "ArchiveListResponse",
    # Admin
    "AdminStatsResponse",
    "UserInfoResponse",
    "ProductInfoResponse",
    "BroadcastRequest",
    # Common
    "HealthResponse",
    "MessageResponse",
    "ErrorResponse",
]
