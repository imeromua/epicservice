"""
Shared authorization dependencies for FastAPI endpoints.

Provides reusable FastAPI Depends-compatible helpers for:
- Extracting user_id from a JWT Bearer Authorization header
- Validating Telegram Mini App (TMA) initData via HMAC-SHA256
- Verifying admin rights (by ADMIN_IDS list)
- Verifying admin-or-moderator rights (ADMIN_IDS or DB role)
- Combined JWT-or-TMA auth for endpoints used by both flows
"""

import hashlib
import hmac as _hmac
import json
import logging
import time
import urllib.parse
from typing import Optional

from fastapi import Depends, Header, HTTPException

from config import ADMIN_IDS
from database.orm.users import orm_get_user_by_id

logger = logging.getLogger(__name__)

# Maximum age of Telegram initData before it is considered expired (24 hours).
_TMA_MAX_AGE_SECONDS = 86_400


def _validate_tma_init_data(init_data: str) -> int:
    """
    Validates a Telegram Mini App initData string using HMAC-SHA256.

    Algorithm (per Telegram docs):
      1. Parse URL-encoded key=value pairs.
      2. Remove the 'hash' field and build a sorted data-check string.
      3. secret_key = HMAC-SHA256(key=b"WebAppData", msg=bot_token)
      4. expected_hash = HMAC-SHA256(key=secret_key, msg=data_check_string)
      5. Compare expected_hash with the received hash (constant-time).

    Also checks auth_date freshness (max _TMA_MAX_AGE_SECONDS).

    Returns the validated Telegram user_id on success.
    Raises HTTP 401 on any validation failure.
    """
    from config import BOT_TOKEN  # local import avoids module-level circular dep

    try:
        params = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))

        received_hash = params.pop("hash", None)
        if not received_hash:
            raise HTTPException(status_code=401, detail="Missing hash in Telegram initData")

        # Freshness check
        auth_date_str = params.get("auth_date")
        if auth_date_str:
            try:
                age = time.time() - int(auth_date_str)
                if age > _TMA_MAX_AGE_SECONDS:
                    raise HTTPException(status_code=401, detail="Telegram initData has expired")
            except ValueError:
                raise HTTPException(status_code=401, detail="Invalid auth_date in Telegram initData")

        # Build data-check string (sorted key=value lines, hash excluded)
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))

        # Derive secret key: HMAC-SHA256("WebAppData", bot_token)
        secret_key = _hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()

        # Compute expected hash
        expected_hash = _hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not _hmac.compare_digest(expected_hash, received_hash):
            raise HTTPException(status_code=401, detail="Invalid Telegram initData signature")

        # Extract user identity
        user_json = params.get("user")
        if not user_json:
            raise HTTPException(status_code=401, detail="No user field in Telegram initData")

        user_data = json.loads(user_json)
        user_id = user_data.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="No user id in Telegram initData")

        return int(user_id)

    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("TMA initData validation error: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid Telegram initData")


# ---------------------------------------------------------------------------
# JWT-based dependencies (standalone / mobile app)
# ---------------------------------------------------------------------------

def get_current_user_id(authorization: str = Header(...)) -> int:
    """
    Extracts and validates user_id from a JWT Bearer token in the Authorization header.

    Raises HTTP 401 if the header is missing, malformed, or the token is invalid/expired.
    """
    from webapp.routers.auth import get_current_user  # local import avoids circular deps

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected: Bearer <token>",
        )
    token = authorization[7:]
    return get_current_user(token)


def require_admin(user_id: int = Depends(get_current_user_id)) -> int:
    """
    Verifies that the JWT-authenticated user is an admin (present in ADMIN_IDS).

    Raises HTTP 403 if the user is not an admin.
    Returns the verified user_id.
    """
    if user_id not in ADMIN_IDS:
        logger.warning("Unauthorized admin access attempt by user %s (JWT)", user_id)
        raise HTTPException(status_code=403, detail="Access denied. Admin rights required.")
    return user_id


async def require_admin_or_moderator(user_id: int = Depends(get_current_user_id)) -> int:
    """
    Verifies that the JWT-authenticated user is an admin or moderator.

    Admins are identified via ADMIN_IDS; moderators are identified by role in the DB.
    Raises HTTP 403 if the user is neither.
    Returns the verified user_id.
    """
    if user_id in ADMIN_IDS:
        return user_id
    user = await orm_get_user_by_id(user_id)
    if user and user.role in ("admin", "moderator"):
        return user_id
    logger.warning("Unauthorized admin/moderator access attempt by user %s (JWT)", user_id)
    raise HTTPException(
        status_code=403,
        detail="Access denied. Admin or moderator rights required.",
    )


# ---------------------------------------------------------------------------
# Telegram Mini App (TMA) dependencies
# ---------------------------------------------------------------------------

def get_tma_user_id(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data"),
) -> int:
    """
    Validates Telegram Mini App initData from the X-Telegram-Init-Data request header.

    Returns the validated Telegram user_id on success.
    Raises HTTP 422 if the header is missing, HTTP 401 if invalid or expired.
    """
    return _validate_tma_init_data(x_telegram_init_data)


def require_tma_admin(user_id: int = Depends(get_tma_user_id)) -> int:
    """
    Verifies that the TMA-authenticated user is an admin (present in ADMIN_IDS).

    Raises HTTP 403 if the user is not an admin.
    Returns the verified user_id.
    """
    if user_id not in ADMIN_IDS:
        logger.warning("Unauthorized TMA admin access attempt by user %s", user_id)
        raise HTTPException(status_code=403, detail="Access denied. Admin rights required.")
    return user_id


async def require_tma_admin_or_moderator(user_id: int = Depends(get_tma_user_id)) -> int:
    """
    Verifies that the TMA-authenticated user is an admin or moderator.

    Raises HTTP 403 if neither.
    Returns the verified user_id.
    """
    if user_id in ADMIN_IDS:
        return user_id
    user = await orm_get_user_by_id(user_id)
    if user and user.role in ("admin", "moderator"):
        return user_id
    logger.warning("Unauthorized TMA admin/moderator access attempt by user %s", user_id)
    raise HTTPException(
        status_code=403,
        detail="Access denied. Admin or moderator rights required.",
    )


# ---------------------------------------------------------------------------
# Combined JWT-or-TMA dependencies (endpoints used by both flows)
# ---------------------------------------------------------------------------

async def _get_user_id_any_auth(
    authorization: Optional[str] = Header(None),
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
) -> int:
    """
    Accepts either a JWT Bearer token (Authorization header) or Telegram initData
    (X-Telegram-Init-Data header) and returns the validated user_id.

    TMA header takes priority when present.
    Raises HTTP 401 if neither valid header is provided.
    """
    if x_telegram_init_data:
        return _validate_tma_init_data(x_telegram_init_data)

    if authorization:
        from webapp.routers.auth import get_current_user  # local import avoids circular deps
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Invalid Authorization header format. Expected: Bearer <token>",
            )
        return get_current_user(authorization[7:])

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide Authorization or X-Telegram-Init-Data header.",
    )


def get_current_user_id_any_auth(user_id: int = Depends(_get_user_id_any_auth)) -> int:
    """Returns user_id validated via JWT or TMA (use as a Depends replacement)."""
    return user_id


async def require_admin_any_auth(user_id: int = Depends(_get_user_id_any_auth)) -> int:
    """
    Verifies that the caller (JWT or TMA) is an admin (present in ADMIN_IDS).

    Raises HTTP 403 if not an admin.
    Returns the verified user_id.
    """
    if user_id not in ADMIN_IDS:
        logger.warning("Unauthorized admin access attempt by user %s (any-auth)", user_id)
        raise HTTPException(status_code=403, detail="Access denied. Admin rights required.")
    return user_id


async def require_admin_or_moderator_any_auth(
    user_id: int = Depends(_get_user_id_any_auth),
) -> int:
    """
    Verifies that the caller (JWT or TMA) is an admin or moderator.

    Raises HTTP 403 if neither.
    Returns the verified user_id.
    """
    if user_id in ADMIN_IDS:
        return user_id
    user = await orm_get_user_by_id(user_id)
    if user and user.role in ("admin", "moderator"):
        return user_id
    logger.warning(
        "Unauthorized admin/moderator access attempt by user %s (any-auth)", user_id
    )
    raise HTTPException(
        status_code=403,
        detail="Access denied. Admin or moderator rights required.",
    )
