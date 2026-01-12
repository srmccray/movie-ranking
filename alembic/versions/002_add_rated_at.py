"""Add rated_at column to rankings table.

Revision ID: 002_add_rated_at
Revises: 001_initial_schema
Create Date: 2026-01-11

This migration adds a rated_at column to allow users to specify
when they rated a movie, defaulting to the current timestamp.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_add_rated_at"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add rated_at column with default to current timestamp."""
    # Add rated_at column
    op.add_column(
        "rankings",
        sa.Column(
            "rated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    # Backfill existing rows to use created_at as their rated_at value
    op.execute("UPDATE rankings SET rated_at = created_at")

    # Create index for sorting by rated_at
    op.create_index(
        "idx_rankings_user_rated_at",
        "rankings",
        ["user_id", sa.text("rated_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    """Remove rated_at column."""
    op.drop_index("idx_rankings_user_rated_at", table_name="rankings")
    op.drop_column("rankings", "rated_at")
