"""Token schemas for authentication responses."""

from pydantic import BaseModel


class Token(BaseModel):
    """OAuth2 token response schema.

    Attributes:
        access_token: The JWT access token string.
        token_type: The token type (always "bearer").
    """

    access_token: str
    token_type: str = "bearer"
