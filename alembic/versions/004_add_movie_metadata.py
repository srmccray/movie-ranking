"""Add movie metadata fields and genres table.

Revision ID: 004_add_movie_metadata
Revises: 003_add_tmdb_fields
Create Date: 2026-01-11

This migration adds additional movie metadata columns to support analytics:
- genre_ids: JSON array of TMDB genre IDs
- vote_average: TMDB user rating (0.0-10.0)
- vote_count: Number of TMDB votes
- release_date: Full release date
- original_language: ISO 639-1 language code
- runtime: Movie length in minutes

Also creates a genres reference table for mapping genre IDs to names.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "004_add_movie_metadata"
down_revision: Union[str, None] = "003_add_tmdb_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add movie metadata columns and genres reference table."""
    # Create genres reference table
    op.create_table(
        "genres",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add genre_ids column (JSON array of TMDB genre IDs)
    op.add_column(
        "movies",
        sa.Column("genre_ids", JSONB(), nullable=True),
    )

    # Add vote_average column (TMDB user rating 0.0-10.0)
    op.add_column(
        "movies",
        sa.Column("vote_average", sa.Float(), nullable=True),
    )

    # Add vote_count column (number of TMDB votes)
    op.add_column(
        "movies",
        sa.Column("vote_count", sa.Integer(), nullable=True),
    )

    # Add release_date column (full date, more precise than year)
    op.add_column(
        "movies",
        sa.Column("release_date", sa.Date(), nullable=True),
    )

    # Add original_language column (ISO 639-1 code, e.g., "en", "fr")
    op.add_column(
        "movies",
        sa.Column("original_language", sa.String(length=10), nullable=True),
    )

    # Add runtime column (movie length in minutes)
    op.add_column(
        "movies",
        sa.Column("runtime", sa.Integer(), nullable=True),
    )

    # Create GIN index on genre_ids for efficient JSON array queries
    op.create_index(
        "idx_movies_genre_ids",
        "movies",
        ["genre_ids"],
        unique=False,
        postgresql_using="gin",
    )

    # Create index on release_date for date range queries
    op.create_index(
        "idx_movies_release_date",
        "movies",
        ["release_date"],
        unique=False,
    )

    # Create index on original_language for filtering
    op.create_index(
        "idx_movies_original_language",
        "movies",
        ["original_language"],
        unique=False,
    )

    # Seed genres table with TMDB movie genres
    # Source: https://api.themoviedb.org/3/genre/movie/list
    genres_table = sa.table(
        "genres",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
    )

    tmdb_genres = [
        {"id": 28, "name": "Action"},
        {"id": 12, "name": "Adventure"},
        {"id": 16, "name": "Animation"},
        {"id": 35, "name": "Comedy"},
        {"id": 80, "name": "Crime"},
        {"id": 99, "name": "Documentary"},
        {"id": 18, "name": "Drama"},
        {"id": 10751, "name": "Family"},
        {"id": 14, "name": "Fantasy"},
        {"id": 36, "name": "History"},
        {"id": 27, "name": "Horror"},
        {"id": 10402, "name": "Music"},
        {"id": 9648, "name": "Mystery"},
        {"id": 10749, "name": "Romance"},
        {"id": 878, "name": "Science Fiction"},
        {"id": 10770, "name": "TV Movie"},
        {"id": 53, "name": "Thriller"},
        {"id": 10752, "name": "War"},
        {"id": 37, "name": "Western"},
    ]

    op.bulk_insert(genres_table, tmdb_genres)


def downgrade() -> None:
    """Remove movie metadata columns and genres table."""
    op.drop_index("idx_movies_original_language", table_name="movies")
    op.drop_index("idx_movies_release_date", table_name="movies")
    op.drop_index("idx_movies_genre_ids", table_name="movies")
    op.drop_column("movies", "runtime")
    op.drop_column("movies", "original_language")
    op.drop_column("movies", "release_date")
    op.drop_column("movies", "vote_count")
    op.drop_column("movies", "vote_average")
    op.drop_column("movies", "genre_ids")
    op.drop_table("genres")
