"""Rate limiting middleware using SlowAPI."""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


def get_user_id_or_ip(request: Request) -> str:
    """
    Get user identifier for rate limiting.
    
    Priority:
    1. Telegram user_id from query params
    2. IP address
    """
    # Try to get user_id from query params
    user_id = request.query_params.get("user_id")
    if user_id:
        return f"user:{user_id}"
    
    # Fallback to IP address
    return get_remote_address(request)


# Initialize limiter
limiter = Limiter(
    key_func=get_user_id_or_ip,
    default_limits=["200/minute"],  # Global limit
    storage_uri="memory://",  # In-memory storage (use Redis in production)
    headers_enabled=True,  # Add rate limit headers to response
)


def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom error handler for rate limit exceeded.
    
    Returns JSON response instead of HTML.
    """
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": "RateLimitExceeded",
            "message": "Too many requests. Please try again later.",
            "details": {
                "retry_after": exc.headers.get("Retry-After"),
                "limit": request.state.view_rate_limit,
            },
        },
        headers=exc.headers,
    )


def setup_rate_limiting(app):
    """
    Setup rate limiting for FastAPI app.
    
    Usage:
        from middlewares.rate_limit import setup_rate_limiting
        
        app = FastAPI()
        setup_rate_limiting(app)
    """
    # Add limiter to app state
    app.state.limiter = limiter
    
    # Add middleware
    app.add_middleware(SlowAPIMiddleware)
    
    # Add custom error handler
    app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)
