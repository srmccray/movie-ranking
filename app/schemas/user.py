"""User schemas for request/response validation."""

from datetime import datetime
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
