"""Rate limit configuration for different endpoints."""

from typing import Dict


class RateLimitConfig:
    """
    Rate limit configurations for API endpoints.
    
    Format: "requests/period"
    Periods: second, minute, hour, day
    """

    # Public endpoints (more restrictive)
    SEARCH = "10/minute"  # Search is expensive
    HEALTH = "60/minute"  # Health check

    # User endpoints
    LIST_GET = "30/minute"  # Get user list
    LIST_ADD = "20/minute"  # Add to list
    LIST_UPDATE = "20/minute"  # Update quantity
    LIST_SAVE = "5/minute"  # Save list (creates Excel)
    ARCHIVE_GET = "20/minute"  # Get archives
    ARCHIVE_DOWNLOAD = "10/minute"  # Download archive
    STATISTICS = "30/minute"  # User statistics

    # Admin endpoints (less restrictive for admins)
    ADMIN_STATS = "60/minute"  # Admin dashboard
    ADMIN_IMPORT = "2/minute"  # Excel import (heavy operation)
    ADMIN_EXPORT = "10/minute"  # Export reports
    ADMIN_BROADCAST = "1/minute"  # Broadcast messages
    ADMIN_FORCE_SAVE = "10/minute"  # Force save user lists

    # Special limits for authenticated users
    AUTHENTICATED_MULTIPLIER = 2  # Authenticated users get 2x limits

    @classmethod
    def get_limit(cls, endpoint: str, is_admin: bool = False) -> str:
        """
        Get rate limit for endpoint.
        
        Args:
            endpoint: Endpoint name
            is_admin: Whether user is admin
            
        Returns:
            Rate limit string
        """
        base_limit = getattr(cls, endpoint.upper(), "30/minute")
        
        if is_admin:
            # Admins get 3x limits
            count, period = base_limit.split("/")
            return f"{int(count) * 3}/{period}"
        
        return base_limit

    @classmethod
    def get_all_limits(cls) -> Dict[str, str]:
        """Get all configured limits as dict."""
        return {
            key: value
            for key, value in cls.__dict__.items()
            if not key.startswith("_") and isinstance(value, str) and "/" in value
        }
