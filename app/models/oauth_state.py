"""OAuth state model for CSRF protection during OAuth flows."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OAuthState(Base):
    """OAuth state model for CSRF protection.

    Stores temporary state tokens used during OAuth flows to prevent
    CSRF attacks. States expire after 5 minutes.

    Attributes:
        id: Unique identifier (UUID).
        state: Cryptographically random state token.
        redirect_uri: Where to redirect after OAuth completes.
        user_id: User ID for account linking flows (nullable for login flows).
        flow_type: Type of OAuth flow ('login' or 'link').
        created_at: Token creation timestamp.
        expires_at: Token expiration timestamp (5 minutes from creation).
    """

    __tablename__ = "oauth_states"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    state: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    redirect_uri: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    flow_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="login",
        server_default=text("'login'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"),
    )
    expires_at: Mapped[datetime] = mapped_column(
        nullable=False,
    )

    __table_args__ = (
        Index("idx_oauth_states_state", "state"),
        Index("idx_oauth_states_expires_at", "expires_at"),
        Index("idx_oauth_states_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        """Return string representation of OAuthState."""
        return f"<OAuthState(state={self.state[:8]}..., flow_type={self.flow_type}, expires_at={self.expires_at})>"
