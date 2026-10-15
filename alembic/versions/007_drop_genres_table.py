"""Drop the unused genres table.

Revision ID: 007_drop_genres_table
Revises: 006_oauth_linking
Create Date: 2026-10-14

The genres reference table (created and seeded in 004) has no readers; genre
names come from GENRE_MAP in app/routers/analytics.py. Downgrade recreates
and reseeds the table so it is lossless.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007_drop_genres_table"
down_revision: Union[str, None] = "006_oauth_linking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Same rows seeded by 004_add_movie_metadata (TMDB movie genre list).
TMDB_GENRES = [
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


def upgrade() -> None:
    """Drop the genres table."""
    op.drop_table("genres")


def downgrade() -> None:
    """Recreate and reseed the genres table."""
    genres_table = op.create_table(
        "genres",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.bulk_insert(genres_table, TMDB_GENRES)
