"""Initial database schema for Movie Ranking API.

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-01-10

This migration creates the initial database schema including:
- users: User accounts with authentication
- movies: Movie information
- rankings: User ratings for movies
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""
    # Create users table
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    # Create index on users.email for fast login lookups
    op.create_index("idx_users_email", "users", ["email"], unique=False)

    # Create movies table
    op.create_table(
        "movies",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "year IS NULL OR (year >= 1888 AND year <= 2031)",
            name="chk_year",
        ),
    )

    # Create indexes on movies table
    op.create_index("idx_movies_title", "movies", ["title"], unique=False)
    op.create_index("idx_movies_year", "movies", ["year"], unique=False)

    # Create rankings table
    op.create_table(
        "rankings",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("movie_id", sa.UUID(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_rankings_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["movie_id"],
            ["movies.id"],
            name="fk_rankings_movie_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("user_id", "movie_id", name="uq_user_movie"),
        sa.CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="chk_rating",
        ),
    )

    # Create indexes on rankings table
    op.create_index("idx_rankings_user_id", "rankings", ["user_id"], unique=False)
    op.create_index("idx_rankings_movie_id", "rankings", ["movie_id"], unique=False)
    op.create_index(
        "idx_rankings_user_updated",
        "rankings",
        ["user_id", sa.text("updated_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    """Drop all tables in reverse order."""
    # Drop rankings table and its indexes
    op.drop_index("idx_rankings_user_updated", table_name="rankings")
    op.drop_index("idx_rankings_movie_id", table_name="rankings")
    op.drop_index("idx_rankings_user_id", table_name="rankings")
    op.drop_table("rankings")

    # Drop movies table and its indexes
    op.drop_index("idx_movies_year", table_name="movies")
    op.drop_index("idx_movies_title", table_name="movies")
    op.drop_table("movies")

    # Drop users table and its indexes
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")
