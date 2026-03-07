"""
Shared authorization dependencies for FastAPI endpoints.

Provides reusable FastAPI Depends-compatible helpers for:
- Extracting user_id from a JWT Bearer Authorization header
- Verifying admin rights (by ADMIN_IDS list)
- Verifying admin-or-moderator rights (ADMIN_IDS or DB role)
"""

import logging

from fastapi import Depends, Header, HTTPException

from config import ADMIN_IDS
from database.orm.users import orm_get_user_by_id

logger = logging.getLogger(__name__)


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
