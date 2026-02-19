"""Common response schemas."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "service": "epicservice",
                "version": "3.0.0",
            }
        }


class MessageResponse(BaseModel):
    """Generic success message response."""

    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[Any] = Field(None, description="Optional additional data")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": None,
            }
        }


class ErrorResponse(BaseModel):
    """Error response."""

    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Any] = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "ValidationError",
                "message": "Invalid input data",
                "details": None,
            }
        }
