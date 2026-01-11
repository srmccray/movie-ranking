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
        hashed_password: bcrypt-hashed password.
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
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
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
    )

    def __repr__(self) -> str:
        """Return string representation of User."""
        return f"<User(id={self.id}, email={self.email})>"
