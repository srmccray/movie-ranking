"""OAuth schemas for Google authentication request/response validation."""

from pydantic import BaseModel, Field


class GoogleAuthUrlResponse(BaseModel):
    """Schema for Google OAuth authorization URL response.

    RESPONSE SHAPE: { authorization_url: "https://accounts.google.com/..." }

    This response contains the URL to redirect the user to for Google authentication.

    Attributes:
        authorization_url: Full Google OAuth URL with state parameter.
    """

    authorization_url: str = Field(
        ...,
        description="Full Google OAuth authorization URL to redirect user to",
    )


class GoogleCallbackError(BaseModel):
    """Schema for OAuth callback error response.

    Attributes:
        error: Error code from the OAuth provider.
        error_description: Human-readable error description.
    """

    error: str = Field(..., description="Error code")
    error_description: str | None = Field(
        None, description="Human-readable error description"
    )


class AccountLinkingResponse(BaseModel):
    """Schema for account linking required response.

    Returned when a Google account email matches an existing account
    that needs to be linked.

    Attributes:
        requires_linking: Always true for this response type.
        email: The email address that exists in the system.
        message: Instructions for the user.
    """

    requires_linking: bool = Field(
        True, description="Indicates that account linking is required"
    )
    email: str = Field(..., description="Email address of the existing account")
    message: str = Field(..., description="User-friendly message about linking")
