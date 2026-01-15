"""User model for authentication and user management."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.ranking import Ranking


class User(Base):
    """User model representing registered accounts.

    Attributes:
        id: Unique identifier (UUID).
        email: User's email address (unique).
        hashed_password: bcrypt-hashed password (nullable for OAuth users).
        google_id: Google OAuth user ID (unique, nullable).
        auth_provider: Authentication provider ("local", "google", or "linked").
        created_at: Account creation timestamp.
        updated_at: Last update timestamp.
        rankings: User's movie rankings (relationship).
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    google_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )
    auth_provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="local",
        server_default=text("'local'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )

    # Relationships
    rankings: Mapped[list["Ranking"]] = relationship(
        "Ranking",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_google_id", "google_id"),
    )

    def __repr__(self) -> str:
        """Return string representation of User."""
        return f"<User(id={self.id}, email={self.email})>"
