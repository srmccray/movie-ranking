"""Genre model for TMDB genre reference data."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Genre(Base):
    """Genre model representing TMDB genre reference data.

    This is a reference table mapping TMDB genre IDs to names.
    Populated from TMDB's genre list API.

    Attributes:
        id: TMDB genre ID (primary key, not auto-generated).
        name: Genre name (e.g., "Action", "Comedy").
    """

    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=False,
    )
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Return string representation of Genre."""
        return f"<Genre(id={self.id}, name={self.name})>"
