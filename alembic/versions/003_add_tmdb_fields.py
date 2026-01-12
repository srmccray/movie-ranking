"""Add TMDB fields to movies table.

Revision ID: 003_add_tmdb_fields
Revises: 002_add_rated_at
Create Date: 2026-01-11

This migration adds tmdb_id and poster_url columns to the movies table
for TMDB integration.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_add_tmdb_fields"
down_revision: Union[str, None] = "002_add_rated_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tmdb_id and poster_url columns to movies table."""
    # Add tmdb_id column (nullable integer for TMDB movie ID)
    op.add_column(
        "movies",
        sa.Column("tmdb_id", sa.Integer(), nullable=True),
    )

    # Add poster_url column (nullable string for poster image URL)
    op.add_column(
        "movies",
        sa.Column("poster_url", sa.String(length=500), nullable=True),
    )

    # Create index on tmdb_id for lookups
    op.create_index(
        "idx_movies_tmdb_id",
        "movies",
        ["tmdb_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove tmdb_id and poster_url columns from movies table."""
    op.drop_index("idx_movies_tmdb_id", table_name="movies")
    op.drop_column("movies", "poster_url")
    op.drop_column("movies", "tmdb_id")
