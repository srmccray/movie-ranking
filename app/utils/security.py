"""Security utilities for password hashing and JWT token handling."""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings

# Bcrypt cost factor (work factor)
BCRYPT_ROUNDS = 12


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password.

    Args:
        plain_password: The plain text password to verify.
        hashed_password: The bcrypt-hashed password to check against.

    Returns:
        True if the password matches, False otherwise.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt with cost factor 12.

    Args:
        password: The plain text password to hash.

    Returns:
        The bcrypt-hashed password string.
    """
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token with the provided data.

    Args:
        data: Dictionary containing claims to encode in the token.
            Should include 'sub' with the user ID.
        expires_delta: Optional custom expiration time delta.
            Defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Encoded JWT token string.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access",
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


class TokenError(Exception):
    """Base exception for token-related errors."""

    pass


class TokenExpiredError(TokenError):
    """Raised when a token has expired."""

    pass


class TokenInvalidError(TokenError):
    """Raised when a token is invalid."""

    pass


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token.

    Args:
        token: The JWT token string to decode.

    Returns:
        Dictionary containing the decoded token claims.

    Raises:
        TokenExpiredError: If the token has expired.
        TokenInvalidError: If the token is invalid or malformed.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        raise TokenExpiredError("Token has expired") from e
    except JWTError as e:
        raise TokenInvalidError("Invalid token") from e
