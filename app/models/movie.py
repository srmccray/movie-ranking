"""Movie model for storing film information."""

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, Float, Index, Integer, JSON, String, text
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
        tmdb_id: The Movie Database (TMDB) ID (optional).
        poster_url: URL to movie poster image (optional).
        genre_ids: JSON array of TMDB genre IDs (optional).
        vote_average: TMDB user rating 0.0-10.0 (optional).
        vote_count: Number of TMDB votes (optional).
        release_date: Full release date (optional).
        original_language: ISO 639-1 language code (optional).
        runtime: Movie length in minutes (optional).
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
    tmdb_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    poster_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    genre_ids: Mapped[list[int] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    vote_average: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    vote_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    release_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    original_language: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    runtime: Mapped[int | None] = mapped_column(
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
        Index("idx_movies_tmdb_id", "tmdb_id"),
    )

    def __repr__(self) -> str:
        """Return string representation of Movie."""
        return f"<Movie(id={self.id}, title={self.title}, year={self.year})>"
