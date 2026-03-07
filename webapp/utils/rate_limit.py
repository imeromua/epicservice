"""
webapp/utils/rate_limit.py

Redis-backed fixed-window rate limiting for abuse protection on auth-sensitive endpoints.

Uses INCR + EXPIRE in Redis for a simple, low-overhead per-scope/identifier counter.
Degrades safely if Redis is None or unavailable: all checks return False (allow),
so the app continues to function when Redis is down.
"""

import logging

logger = logging.getLogger(__name__)

# Redis key prefix for all rate-limit counters
_RL_PREFIX = "rl:"


def _rl_key(scope: str, identifier: str) -> str:
    """Build a Redis key for the given scope and identifier."""
    return f"{_RL_PREFIX}{scope}:{identifier}"


async def is_rate_limited(
    redis,
    scope: str,
    identifier: str,
    max_requests: int,
    window_seconds: int,
) -> bool:
    """
    Check and record a rate-limited request using a fixed-window counter in Redis.

    Returns True if the caller is over the limit (request should be blocked),
    False if within limits (request proceeds).

    Degrades safely: returns False (allow) if redis is None or a Redis error occurs,
    so the app continues to work when Redis is unavailable.

    Args:
        redis: Redis asyncio client (or None for graceful degradation).
        scope: Logical scope name, e.g. "otp_ip". Must not contain sensitive data.
        identifier: Per-caller identifier, e.g. IP address or phone number.
                    Not logged beyond truncation for safety.
        max_requests: Maximum number of requests allowed within the window.
        window_seconds: Duration of the rate-limit window in seconds.

    Returns:
        True if rate limit is exceeded (block the request), False otherwise.
    """
    if redis is None:
        return False  # Graceful degradation: no Redis, no rate limiting

    key = _rl_key(scope, identifier)
    try:
        current = await redis.incr(key)
        if current == 1:
            # First request in this window — set the expiry
            await redis.expire(key, window_seconds)
        if current > max_requests:
            logger.warning(
                "Rate limit exceeded: scope=%s count=%d limit=%d window=%ds",
                scope,
                current,
                max_requests,
                window_seconds,
            )
            return True
        return False
    except Exception as exc:
        # Redis error — fail open to avoid blocking legitimate requests
        logger.warning("Rate limiter Redis error (scope=%s): %s", scope, exc)
        return False
