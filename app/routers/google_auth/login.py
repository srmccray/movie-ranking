"""Google OAuth router for authentication with Google accounts."""

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.config import settings
from app.database import DbSession
from app.models.user import User
from app.routers.google_auth import link, oauth, redirects
from app.schemas.oauth import GoogleAuthUrlResponse
from app.schemas.token import Token
from app.utils.cookies import set_session_cookies
from app.utils.security import create_access_token

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/google/login/",
    response_model=GoogleAuthUrlResponse,
    summary="Initiate Google OAuth login",
    responses={
        200: {"description": "Returns Google authorization URL"},
        400: {"description": "Invalid redirect_uri"},
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

    redirects.validate_redirect_uri(redirect_uri)

    # Create state token for CSRF protection
    state = await oauth._create_state_token(db, redirect_uri)

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
    "/google/callback/",
    response_model=Token,
    summary="Handle Google OAuth callback",
    responses={
        200: {"description": "Authentication successful, returns JWT token"},
        400: {"description": "Invalid state, code, or authentication cancelled"},
    },
)
async def google_callback(
    request: Request,
    db: DbSession,
    response: Response,
    code: str | None = Query(None, description="Authorization code from Google"),
    state: str | None = Query(None, description="State token for CSRF validation"),
    error: str | None = Query(None, description="Error code if user denied access"),
) -> Token | RedirectResponse:
    """Handle the OAuth callback from Google.

    Validates the state token, exchanges the authorization code for tokens,
    verifies the ID token, and creates or finds the user account.

    Args:
        request: Incoming request (session cookie for link-flow binding).
        db: Async database session.
        response: Response used to attach the session cookies to JSON replies.
        code: Authorization code from Google.
        state: State token for CSRF validation.
        error: Error code if the user denied access.

    Returns:
        A 302 to the stored redirect_uri, or the Token JSON when none was
        stored. Both set the httpOnly session cookie and the CSRF cookie. The
        redirect ``Location`` is the stored URL unchanged: it never carries the
        token.

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
    oauth_state = await oauth._validate_state_token(db, state)
    if oauth_state is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired authentication state",
        )

    # Store state info before deleting (re-validate stored value, defense in depth)
    custom_redirect_uri = oauth_state.redirect_uri
    if not redirects.is_valid_redirect_uri(custom_redirect_uri):
        logger.warning("Discarding invalid stored redirect_uri")
        custom_redirect_uri = None
    flow_type = oauth_state.flow_type
    linking_user_id = oauth_state.user_id

    # Delete the used state token
    await db.delete(oauth_state)
    await db.flush()

    # If this is a link flow, handle it separately
    if flow_type == "link" and linking_user_id is not None:
        if not link.session_matches_user(request, linking_user_id):
            logger.warning("Link callback rejected: session does not match user")
            return RedirectResponse(
                url=f"{custom_redirect_uri or '/settings'}?error=session_mismatch",
                status_code=status.HTTP_302_FOUND,
            )
        return await link._handle_link_callback(
            db, code, custom_redirect_uri, linking_user_id
        )

    # Exchange code for tokens
    tokens = await oauth._exchange_code_for_tokens(code)

    # Verify ID token
    id_token_str = tokens.get("id_token")
    if not id_token_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No ID token received",
        )

    idinfo = oauth._verify_google_id_token(id_token_str)

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

    if custom_redirect_uri:
        # The session cookie authenticates the SPA; the URL never carries the JWT.
        redirect = RedirectResponse(
            url=custom_redirect_uri, status_code=status.HTTP_302_FOUND
        )
        set_session_cookies(redirect, access_token)
        return redirect

    set_session_cookies(response, access_token)
    return Token(access_token=access_token)
