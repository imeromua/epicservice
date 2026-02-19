"""Logging middleware for FastAPI with correlation ID."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from utils.logger import api_logger, set_correlation_id, clear_correlation_id


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs all requests with correlation ID."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log request and response with timing and correlation ID.
        
        Correlation ID priority:
        1. X-Correlation-ID header (from client)
        2. Generate new UUID
        """
        # Get or generate correlation ID
        correlation_id = request.headers.get(
            "X-Correlation-ID", str(uuid.uuid4())
        )
        set_correlation_id(correlation_id)

        # Log request
        start_time = time.time()
        api_logger.info(
            f"Request started: {request.method} {request.url.path}",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        # Process request
        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Log response
            api_logger.info(
                f"Request completed: {request.method} {request.url.path}",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            return response

        except Exception as exc:
            duration = time.time() - start_time

            # Log error
            api_logger.exception(
                f"Request failed: {request.method} {request.url.path}",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
                error=str(exc),
            )

            raise

        finally:
            # Clear correlation ID from context
            clear_correlation_id()


def setup_logging(app):
    """
    Setup logging middleware for FastAPI app.
    
    Usage:
        from middlewares.logging_middleware import setup_logging
        
        app = FastAPI()
        setup_logging(app)
    """
    app.add_middleware(LoggingMiddleware)
