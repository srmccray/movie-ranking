"""Google OAuth router for authentication with Google accounts."""

import logging
import secrets
from datetime import datetime, timedelta
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import delete, select

from app.config import settings
from app.database import DbSession
from app.models.oauth_state import OAuthState

logger = logging.getLogger(__name__)


# Google OAuth URLs
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# OAuth state expiration time (5 minutes)
STATE_EXPIRATION_MINUTES = 5


async def _cleanup_expired_states(db: DbSession) -> None:
    """Remove expired OAuth state tokens from the database.

    Args:
        db: Async database session.
    """
    now = datetime.utcnow()
    await db.execute(delete(OAuthState).where(OAuthState.expires_at < now))


async def _create_state_token(
    db: DbSession,
    redirect_uri: str | None = None,
    user_id: UUID | None = None,
    flow_type: str = "login",
) -> str:
    """Create and store a cryptographically secure state token.

    Args:
        db: Async database session.
        redirect_uri: Optional URI to redirect to after OAuth completes.
        user_id: Optional user ID for account linking flows.
        flow_type: Type of OAuth flow ('login' or 'link').

    Returns:
        The generated state token string.
    """
    # Clean up expired states periodically
    await _cleanup_expired_states(db)

    # Generate cryptographically random state
    state = secrets.token_urlsafe(32)

    # Calculate expiration time (naive UTC per project convention)
    expires_at = datetime.utcnow() + timedelta(minutes=STATE_EXPIRATION_MINUTES)

    # Store state in database
    oauth_state = OAuthState(
        state=state,
        redirect_uri=redirect_uri,
        user_id=user_id,
        flow_type=flow_type,
        expires_at=expires_at,
    )
    db.add(oauth_state)
    await db.flush()

    return state


async def _validate_state_token(db: DbSession, state: str) -> OAuthState | None:
    """Validate and retrieve an OAuth state token.

    Args:
        db: Async database session.
        state: The state token to validate.

    Returns:
        The OAuthState object if valid and not expired, None otherwise.
    """
    result = await db.execute(select(OAuthState).where(OAuthState.state == state))
    oauth_state = result.scalar_one_or_none()

    if oauth_state is None:
        return None

    # Check if expired (using naive UTC)
    now = datetime.utcnow()
    # Ensure expires_at is naive for comparison (asyncpg may return tz-aware)
    expires_at = oauth_state.expires_at
    if expires_at.tzinfo is not None:
        expires_at = expires_at.replace(tzinfo=None)
    if expires_at < now:
        # Delete expired state
        await db.delete(oauth_state)
        await db.flush()
        return None

    return oauth_state


async def _exchange_code_for_tokens(code: str) -> dict:
    """Exchange authorization code for Google tokens.

    Args:
        code: The authorization code from Google.

    Returns:
        Dictionary containing id_token and access_token.

    Raises:
        HTTPException: If the token exchange fails.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code",
            )

        return response.json()


def _verify_google_id_token(token: str) -> dict:
    """Verify Google ID token and extract claims.

    Args:
        token: The Google ID token to verify.

    Returns:
        Dictionary containing the verified claims.

    Raises:
        HTTPException: If token verification fails.
    """
    try:
        # Verify the ID token
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )

        # Verify issuer
        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Invalid issuer")

        return idinfo

    except ValueError as e:
        logger.error(f"ID token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID token",
        )
