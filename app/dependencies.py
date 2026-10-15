"""FastAPI dependencies for authentication and authorization."""

import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import DbSession
from app.models.user import User
from app.observability.logging_config import bind_user_id
from app.utils.cookies import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE
from app.utils.security import TokenError, decode_token

# OAuth2 scheme for bearer token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _verify_csrf(request: Request) -> None:
    """Enforce the double-submit CSRF token for cookie-authenticated requests."""
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get(CSRF_HEADER)
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or invalid",
        )


async def get_current_user(
    request: Request,
    bearer_token: Annotated[str | None, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    """Get the current authenticated user from the JWT token.

    Args:
        request: The incoming request (for the session cookie and CSRF check).
        bearer_token: The JWT from the Authorization header, if present.
        db: Async database session.

    Returns:
        The authenticated User model instance.

    Raises:
        HTTPException: 401 Unauthorized if token is invalid or user not found;
            403 if a cookie-authenticated unsafe request lacks a valid CSRF token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if bearer_token:
        # Header auth is not ambient in browsers, so it is CSRF-exempt.
        token = bearer_token
    else:
        cookie_token = request.cookies.get(SESSION_COOKIE)
        if not cookie_token:
            raise credentials_exception
        token = cookie_token

    try:
        payload = decode_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except TokenError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    # Checked after the token so invalid cookies stay 401, not 403.
    if not bearer_token and request.method in UNSAFE_METHODS:
        _verify_csrf(request)

    bind_user_id(user.id)
    return user


# Type alias for dependency injection of current authenticated user
CurrentUser = Annotated[User, Depends(get_current_user)]
