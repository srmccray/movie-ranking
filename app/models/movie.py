"""Movie model for storing film information."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.ranking import Ranking


class Movie(Base):
    """Movie model representing films in the database.

    Attributes:
        id: Unique identifier (UUID).
        title: Movie title.
        year: Release year (optional, must be between 1888 and 2031).
        created_at: Record creation timestamp.
        updated_at: Last update timestamp.
        rankings: Rankings for this movie (relationship).
    """

    __tablename__ = "movies"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
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
        back_populates="movie",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "year IS NULL OR (year >= 1888 AND year <= 2031)",
            name="chk_year",
        ),
        Index("idx_movies_title", "title"),
        Index("idx_movies_year", "year"),
    )

    def __repr__(self) -> str:
        """Return string representation of Movie."""
        return f"<Movie(id={self.id}, title={self.title}, year={self.year})>"
