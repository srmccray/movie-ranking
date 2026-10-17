"""Google OAuth router for authentication with Google accounts."""

import logging
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.config import settings
from app.database import DbSession
from app.dependencies import CurrentUser
from app.models.user import User
from app.routers.google_auth import oauth, redirects
from app.utils.cookies import SESSION_COOKIE
from app.utils.security import TokenError, decode_token
from app.schemas.oauth import GoogleAuthUrlResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def session_matches_user(request: Request, user_id: UUID) -> bool:
    """True if the browser's session cookie belongs to ``user_id``.

    Binds a link-flow callback to the browser that started it, so a victim who
    completes an attacker-initiated Google consent cannot attach their Google
    identity to the attacker's account.
    """
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return False
    try:
        return decode_token(token).get("sub") == str(user_id)
    except TokenError:
        return False


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
    # Default redirect if none specified or the stored value is not allowed
    if not redirect_uri or not redirects.is_valid_redirect_uri(redirect_uri):
        redirect_uri = "/"

    # Exchange code for tokens
    try:
        tokens = await oauth._exchange_code_for_tokens(code)
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
        idinfo = oauth._verify_google_id_token(id_token_str)
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
    "/google/link/",
    response_model=GoogleAuthUrlResponse,
    summary="Initiate Google account linking",
    responses={
        200: {"description": "Returns Google authorization URL for linking"},
        400: {"description": "Invalid redirect_uri"},
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

    redirects.validate_redirect_uri(redirect_uri)

    # Check if user already has Google account linked
    if current_user.google_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Google account already linked",
        )

    # Create state token with user_id for linking flow
    state = await oauth._create_state_token(
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

    authorization_url = f"{oauth.GOOGLE_AUTH_URL}?{urlencode(params)}"

    return GoogleAuthUrlResponse(authorization_url=authorization_url)


@router.get(
    "/google/link/callback/",
    response_class=RedirectResponse,
    response_model=None,
    status_code=status.HTTP_302_FOUND,
    summary="Handle Google account linking callback",
    responses={
        302: {"description": "Redirect to frontend with success or error"},
        400: {"description": "Invalid state, code, or linking cancelled"},
    },
)
async def google_link_callback(
    request: Request,
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
    oauth_state = await oauth._validate_state_token(db, state)
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

    # The callback must come from the browser session that started the flow
    if not session_matches_user(request, linking_user_id):
        logger.warning("Link callback rejected: session does not match user")
        return RedirectResponse(
            url=f"{custom_redirect_uri}?error=session_mismatch",
            status_code=status.HTTP_302_FOUND,
        )

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
        tokens = await oauth._exchange_code_for_tokens(code)
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
        idinfo = oauth._verify_google_id_token(id_token_str)
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
