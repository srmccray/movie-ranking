"""Authentication router for user registration and login."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.database import DbSession
from app.dependencies import CurrentUser
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserProfileResponse
from app.utils.security import create_access_token, get_password_hash, verify_password

router = APIRouter(tags=["auth"])


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        201: {"description": "Account created successfully"},
        409: {"description": "Email already registered"},
        422: {"description": "Validation error"},
    },
)
async def register(user_data: UserCreate, db: DbSession) -> Token:
    """Create a new user account and return an access token.

    Args:
        user_data: User registration data containing email and password.
        db: Async database session.

    Returns:
        Token containing the JWT access token.

    Raises:
        HTTPException: 409 Conflict if email is already registered.
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create new user with hashed password
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
    )

    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    # Generate access token
    access_token = create_access_token(data={"sub": str(new_user.id)})

    return Token(access_token=access_token)


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate and get token",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
    },
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> Token:
    """Authenticate user and return an access token.

    Uses OAuth2 password flow format where the username field contains the email.

    Args:
        form_data: OAuth2 form containing username (email) and password.
        db: Async database session.

    Returns:
        Token containing the JWT access token.

    Raises:
        HTTPException: 401 Unauthorized if credentials are invalid.
    """
    # Find user by email (username field contains email in OAuth2 flow)
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    # Verify user exists and password matches
    # Note: Users without a password (Google-only) cannot use password login
    if (
        user is None
        or user.hashed_password is None
        or not verify_password(form_data.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate access token
    access_token = create_access_token(data={"sub": str(user.id)})

    return Token(access_token=access_token)


@router.get(
    "/me/",
    response_model=UserProfileResponse,
    summary="Get current user profile",
    responses={
        200: {"description": "User profile retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_current_user_profile(
    current_user: CurrentUser,
) -> UserProfileResponse:
    """Get the authenticated user's profile information.

    Returns:
        UserProfileResponse: User profile including authentication provider info.
            - id: User's unique identifier
            - email: User's email address
            - auth_provider: 'local', 'google', or 'linked'
            - has_google_linked: True if Google account is linked
            - has_password: True if user can use email/password login
            - created_at: Account creation timestamp
    """
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        auth_provider=current_user.auth_provider,
        has_google_linked=current_user.google_id is not None,
        has_password=current_user.hashed_password is not None,
        created_at=current_user.created_at,
    )
