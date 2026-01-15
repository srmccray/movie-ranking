"""User schemas for request/response validation."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration requests.

    Attributes:
        email: Valid email address for the user account.
        password: Password with minimum 8 characters.
    """

    email: EmailStr
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    """Schema for user data in responses.

    Attributes:
        id: Unique identifier for the user.
        email: User's email address.
        created_at: Timestamp when the account was created.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    created_at: datetime


class UserProfileResponse(BaseModel):
    """Schema for user profile response with authentication details.

    RESPONSE SHAPE: { id: "uuid", email: "...", auth_provider: "...", ... }

    This response includes the user's authentication provider information
    to allow the frontend to display link status.

    Attributes:
        id: Unique identifier for the user.
        email: User's email address.
        auth_provider: Authentication method ('local', 'google', or 'linked').
        has_google_linked: Whether the user has a Google account linked.
        has_password: Whether the user has a password set (can use email/password login).
        created_at: Timestamp when the account was created.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    auth_provider: Literal["local", "google", "linked"]
    has_google_linked: bool = Field(
        ..., description="True if user has a Google account linked"
    )
    has_password: bool = Field(
        ..., description="True if user has a password set for email/password login"
    )
    created_at: datetime
