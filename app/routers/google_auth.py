"""Google OAuth router for authentication with Google accounts."""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import delete, select

from app.config import settings
from app.database import DbSession
from app.dependencies import CurrentUser
from app.models.oauth_state import OAuthState
from app.models.user import User
from app.schemas.oauth import GoogleAuthUrlResponse
from app.schemas.token import Token
from app.utils.security import create_access_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

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


async def _handle_link_callback(
    db: DbSession,
    code: str,
    redirect_uri: str | None,
    user_id: UUID,
) -> RedirectResponse:
    """Handle OAuth callback for account linking flow.

    Args:
        db: Async database session.
        code: Authorization code from Google.
        redirect_uri: URI to redirect to after linking.
        user_id: ID of user initiating the link.

    Returns:
        RedirectResponse to the redirect_uri with success/error params.
    """
    # Default redirect if none specified
    if not redirect_uri:
        redirect_uri = "/"

    # Exchange code for tokens
    try:
        tokens = await _exchange_code_for_tokens(code)
    except HTTPException:
        return RedirectResponse(
            url=f"{redirect_uri}?error=token_exchange_failed",
            status_code=status.HTTP_302_FOUND,
        )

    # Verify ID token
    id_token_str = tokens.get("id_token")
    if not id_token_str:
        return RedirectResponse(
            url=f"{redirect_uri}?error=no_id_token",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        idinfo = _verify_google_id_token(id_token_str)
    except HTTPException:
        return RedirectResponse(
            url=f"{redirect_uri}?error=invalid_token",
            status_code=status.HTTP_302_FOUND,
        )

    # Extract Google ID
    google_id = idinfo["sub"]
    email = idinfo.get("email")
    email_verified = idinfo.get("email_verified", False)

    if not email_verified:
        return RedirectResponse(
            url=f"{redirect_uri}?error=email_not_verified",
            status_code=status.HTTP_302_FOUND,
        )

    # Find the user that initiated the linking
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        logger.error(f"User not found during link callback: {user_id}")
        return RedirectResponse(
            url=f"{redirect_uri}?error=user_not_found",
            status_code=status.HTTP_302_FOUND,
        )

    # Check if this Google account is already linked to another user
    result = await db.execute(select(User).where(User.google_id == google_id))
    existing_google_user = result.scalar_one_or_none()

    if existing_google_user is not None:
        if existing_google_user.id != user.id:
            logger.warning(
                f"Google account {google_id} already linked to user {existing_google_user.id}"
            )
            return RedirectResponse(
                url=f"{redirect_uri}?error=already_linked_other",
                status_code=status.HTTP_302_FOUND,
            )
        # Already linked to this same user
        return RedirectResponse(
            url=f"{redirect_uri}?linked=success",
            status_code=status.HTTP_302_FOUND,
        )

    # Link Google account to user
    user.google_id = google_id
    user.auth_provider = "linked"
    await db.flush()

    logger.info(f"Linked Google account to user {user.email}")

    return RedirectResponse(
        url=f"{redirect_uri}?linked=success",
        status_code=status.HTTP_302_FOUND,
    )


@router.get(
    "/google/login/",
    response_model=GoogleAuthUrlResponse,
    summary="Initiate Google OAuth login",
    responses={
        200: {"description": "Returns Google authorization URL"},
        500: {"description": "Google OAuth not configured"},
    },
)
async def google_login(
    db: DbSession,
    redirect_uri: str | None = Query(
        None,
        description="Optional URI to redirect to after successful authentication",
    ),
) -> GoogleAuthUrlResponse:
    """Initiate Google OAuth flow by returning the authorization URL.

    Generates a cryptographically secure state token for CSRF protection
    and constructs the Google OAuth authorization URL.

    Args:
        db: Async database session.
        redirect_uri: Optional custom redirect URI after OAuth completes.

    Returns:
        GoogleAuthUrlResponse containing the full authorization URL.

    Raises:
        HTTPException: 500 if Google OAuth is not configured.
    """
    # Check if Google OAuth is configured
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured",
        )

    # Create state token for CSRF protection
    state = await _create_state_token(db, redirect_uri)

    # Build authorization URL
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }

    authorization_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    return GoogleAuthUrlResponse(authorization_url=authorization_url)


@router.get(
    "/google/callback/",
    response_model=Token,
    summary="Handle Google OAuth callback",
    responses={
        200: {"description": "Authentication successful, returns JWT token"},
        400: {"description": "Invalid state, code, or authentication cancelled"},
    },
)
async def google_callback(
    db: DbSession,
    code: str | None = Query(None, description="Authorization code from Google"),
    state: str | None = Query(None, description="State token for CSRF validation"),
    error: str | None = Query(None, description="Error code if user denied access"),
) -> Token | RedirectResponse:
    """Handle the OAuth callback from Google.

    Validates the state token, exchanges the authorization code for tokens,
    verifies the ID token, and creates or finds the user account.

    Args:
        db: Async database session.
        code: Authorization code from Google.
        state: State token for CSRF validation.
        error: Error code if the user denied access.

    Returns:
        Token containing the JWT access token for the user.

    Raises:
        HTTPException: Various errors for invalid state, cancelled auth, etc.
    """
    # Handle user cancellation
    if error:
        logger.info(f"OAuth cancelled by user: {error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication cancelled",
        )

    # Validate required parameters
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required parameters",
        )

    # Validate state token (CSRF protection)
    oauth_state = await _validate_state_token(db, state)
    if oauth_state is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired authentication state",
        )

    # Store state info before deleting
    custom_redirect_uri = oauth_state.redirect_uri
    flow_type = oauth_state.flow_type
    linking_user_id = oauth_state.user_id

    # Delete the used state token
    await db.delete(oauth_state)
    await db.flush()

    # If this is a link flow, handle it separately
    if flow_type == "link" and linking_user_id is not None:
        return await _handle_link_callback(
            db, code, custom_redirect_uri, linking_user_id
        )

    # Exchange code for tokens
    tokens = await _exchange_code_for_tokens(code)

    # Verify ID token
    id_token_str = tokens.get("id_token")
    if not id_token_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No ID token received",
        )

    idinfo = _verify_google_id_token(id_token_str)

    # Extract user info from ID token
    google_id = idinfo["sub"]
    email = idinfo.get("email")
    email_verified = idinfo.get("email_verified", False)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by Google",
        )

    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified with Google",
        )

    # Normalize email to lowercase
    email = email.lower()

    # Try to find user by google_id first
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user is None:
        # Try to find user by email
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is not None:
            # Link Google account to existing user
            user.google_id = google_id
            user.auth_provider = "linked"
            await db.flush()
            logger.info(f"Linked Google account to existing user: {email}")
        else:
            # Create new user with Google account
            user = User(
                email=email,
                google_id=google_id,
                auth_provider="google",
                hashed_password=None,  # No password for Google-only users
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)
            logger.info(f"Created new user with Google account: {email}")

    # Generate JWT token
    access_token = create_access_token(data={"sub": str(user.id)})

    # If custom redirect URI was specified, redirect with token
    if custom_redirect_uri:
        redirect_url = f"{custom_redirect_uri}?token={access_token}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    return Token(access_token=access_token)


@router.get(
    "/google/link/",
    response_model=GoogleAuthUrlResponse,
    summary="Initiate Google account linking",
    responses={
        200: {"description": "Returns Google authorization URL for linking"},
        401: {"description": "Not authenticated"},
        409: {"description": "User already has Google account linked"},
        500: {"description": "Google OAuth not configured"},
    },
)
async def google_link(
    db: DbSession,
    current_user: CurrentUser,
    redirect_uri: str | None = Query(
        None,
        description="URI to redirect to after linking completes",
    ),
) -> GoogleAuthUrlResponse:
    """Initiate Google OAuth flow for account linking.

    This endpoint is for authenticated users who want to link their
    existing account with Google for alternative sign-in.

    Args:
        db: Async database session.
        current_user: The authenticated user requesting the link.
        redirect_uri: Optional custom redirect URI after linking completes.

    Returns:
        GoogleAuthUrlResponse containing the full authorization URL.

    Raises:
        HTTPException: 409 if user already has Google linked.
        HTTPException: 500 if Google OAuth is not configured.
    """
    # Check if Google OAuth is configured
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured",
        )

    # Check if user already has Google account linked
    if current_user.google_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Google account already linked",
        )

    # Create state token with user_id for linking flow
    state = await _create_state_token(
        db,
        redirect_uri=redirect_uri,
        user_id=current_user.id,
        flow_type="link",
    )

    # Build authorization URL
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }

    authorization_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    return GoogleAuthUrlResponse(authorization_url=authorization_url)


@router.get(
    "/google/link/callback/",
    summary="Handle Google account linking callback",
    responses={
        302: {"description": "Redirect to frontend with success or error"},
        400: {"description": "Invalid state, code, or linking cancelled"},
    },
)
async def google_link_callback(
    db: DbSession,
    code: str | None = Query(None, description="Authorization code from Google"),
    state: str | None = Query(None, description="State token for CSRF validation"),
    error: str | None = Query(None, description="Error code if user denied access"),
) -> RedirectResponse:
    """Handle the OAuth callback for Google account linking.

    Validates the state token, exchanges the authorization code for tokens,
    verifies the ID token, and links the Google account to the user.

    Args:
        db: Async database session.
        code: Authorization code from Google.
        state: State token for CSRF validation.
        error: Error code if the user denied access.

    Returns:
        RedirectResponse to the frontend settings page with result.
    """
    # Default redirect for errors
    error_redirect = "/settings"

    # Handle user cancellation
    if error:
        logger.info(f"OAuth linking cancelled by user: {error}")
        return RedirectResponse(
            url=f"{error_redirect}?error=cancelled",
            status_code=status.HTTP_302_FOUND,
        )

    # Validate required parameters
    if not code or not state:
        return RedirectResponse(
            url=f"{error_redirect}?error=invalid_request",
            status_code=status.HTTP_302_FOUND,
        )

    # Validate state token (CSRF protection)
    oauth_state = await _validate_state_token(db, state)
    if oauth_state is None:
        return RedirectResponse(
            url=f"{error_redirect}?error=invalid_state",
            status_code=status.HTTP_302_FOUND,
        )

    # Verify this is a link flow with a user_id
    if oauth_state.flow_type != "link" or oauth_state.user_id is None:
        await db.delete(oauth_state)
        await db.flush()
        return RedirectResponse(
            url=f"{error_redirect}?error=invalid_flow",
            status_code=status.HTTP_302_FOUND,
        )

    # Store user_id and redirect URI before deleting state
    linking_user_id = oauth_state.user_id
    custom_redirect_uri = oauth_state.redirect_uri or error_redirect

    # Delete the used state token
    await db.delete(oauth_state)
    await db.flush()

    # Find the user that initiated the linking
    result = await db.execute(select(User).where(User.id == linking_user_id))
    user = result.scalar_one_or_none()

    if user is None:
        logger.error(f"User not found during link callback: {linking_user_id}")
        return RedirectResponse(
            url=f"{custom_redirect_uri}?error=user_not_found",
            status_code=status.HTTP_302_FOUND,
        )

    # Exchange code for tokens
    try:
        tokens = await _exchange_code_for_tokens(code)
    except HTTPException:
        return RedirectResponse(
            url=f"{custom_redirect_uri}?error=token_exchange_failed",
            status_code=status.HTTP_302_FOUND,
        )

    # Verify ID token
    id_token_str = tokens.get("id_token")
    if not id_token_str:
        return RedirectResponse(
            url=f"{custom_redirect_uri}?error=no_id_token",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        idinfo = _verify_google_id_token(id_token_str)
    except HTTPException:
        return RedirectResponse(
            url=f"{custom_redirect_uri}?error=invalid_token",
            status_code=status.HTTP_302_FOUND,
        )

    # Extract Google ID
    google_id = idinfo["sub"]
    email_verified = idinfo.get("email_verified", False)

    if not email_verified:
        return RedirectResponse(
            url=f"{custom_redirect_uri}?error=email_not_verified",
            status_code=status.HTTP_302_FOUND,
        )

    # Check if this Google account is already linked to another user
    result = await db.execute(select(User).where(User.google_id == google_id))
    existing_google_user = result.scalar_one_or_none()

    if existing_google_user is not None:
        if existing_google_user.id != user.id:
            logger.warning(
                f"Google account {google_id} already linked to user {existing_google_user.id}"
            )
            return RedirectResponse(
                url=f"{custom_redirect_uri}?error=already_linked_other",
                status_code=status.HTTP_302_FOUND,
            )
        # Already linked to this same user (shouldn't happen but handle gracefully)
        return RedirectResponse(
            url=f"{custom_redirect_uri}?linked=success",
            status_code=status.HTTP_302_FOUND,
        )

    # Link Google account to user
    user.google_id = google_id
    user.auth_provider = "linked"
    await db.flush()

    logger.info(f"Linked Google account to user: {user.email}")

    return RedirectResponse(
        url=f"{custom_redirect_uri}?linked=success",
        status_code=status.HTTP_302_FOUND,
    )
