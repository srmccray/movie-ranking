"""Add Google OAuth fields to users and create oauth_states table.

Revision ID: 005_add_google_oauth_fields
Revises: 004_add_movie_metadata
Create Date: 2026-01-14

This migration adds support for Google OAuth authentication:
- google_id: Unique Google user ID for OAuth users
- auth_provider: Track authentication method (local/google/linked)
- hashed_password: Make nullable for OAuth-only users
- oauth_states: Table for CSRF state token storage during OAuth flows
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_add_google_oauth_fields"
down_revision: Union[str, None] = "004_add_movie_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Google OAuth fields and oauth_states table."""
    # Add google_id column to users (unique Google user ID)
    op.add_column(
        "users",
        sa.Column("google_id", sa.String(length=255), nullable=True),
    )

    # Add auth_provider column to users with default "local"
    op.add_column(
        "users",
        sa.Column(
            "auth_provider",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'local'"),
        ),
    )

    # Make hashed_password nullable (Google-only users won't have one)
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=255),
        nullable=True,
    )

    # Create unique index on google_id
    op.create_index(
        "idx_users_google_id",
        "users",
        ["google_id"],
        unique=True,
    )

    # Create oauth_states table for CSRF token storage
    op.create_table(
        "oauth_states",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("state", sa.String(length=255), nullable=False),
        sa.Column("redirect_uri", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes on oauth_states
    op.create_index(
        "idx_oauth_states_state",
        "oauth_states",
        ["state"],
        unique=True,
    )
    op.create_index(
        "idx_oauth_states_expires_at",
        "oauth_states",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove Google OAuth fields and oauth_states table."""
    # Drop oauth_states table and its indexes
    op.drop_index("idx_oauth_states_expires_at", table_name="oauth_states")
    op.drop_index("idx_oauth_states_state", table_name="oauth_states")
    op.drop_table("oauth_states")

    # Drop google_id index and column
    op.drop_index("idx_users_google_id", table_name="users")
    op.drop_column("users", "google_id")

    # Drop auth_provider column
    op.drop_column("users", "auth_provider")

    # Make hashed_password non-nullable again
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=255),
        nullable=False,
    )
