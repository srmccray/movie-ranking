"""Ranking model for user movie ratings."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    desc,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.movie import Movie
from app.models.user import User


class Ranking(Base):
    """Ranking model representing user ratings for movies.

    Attributes:
        id: Unique identifier (UUID).
        user_id: Foreign key to users table.
        movie_id: Foreign key to movies table.
        rating: User's rating (1-5).
        created_at: Initial ranking timestamp.
        updated_at: Last rating update timestamp.
        user: Associated User (relationship).
        movie: Associated Movie (relationship).
    """

    __tablename__ = "rankings"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    movie_id: Mapped[UUID] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(
        Integer,
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
    user: Mapped["User"] = relationship(
        "User",
        back_populates="rankings",
        lazy="joined",
    )
    movie: Mapped["Movie"] = relationship(
        "Movie",
        back_populates="rankings",
        lazy="joined",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uq_user_movie"),
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="chk_rating",
        ),
        Index("idx_rankings_user_id", "user_id"),
        Index("idx_rankings_movie_id", "movie_id"),
        Index(
            "idx_rankings_user_updated",
            "user_id",
            desc("updated_at"),
        ),
    )

    def __repr__(self) -> str:
        """Return string representation of Ranking."""
        return f"<Ranking(id={self.id}, user_id={self.user_id}, movie_id={self.movie_id}, rating={self.rating})>"
