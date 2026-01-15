"""Add user_id and flow_type fields to oauth_states for account linking.

Revision ID: 006_oauth_linking
Revises: 005_add_google_oauth_fields
Create Date: 2026-01-14

This migration extends oauth_states to support account linking:
- user_id: References the user initiating a link flow (nullable for login flows)
- flow_type: Distinguishes between 'login' and 'link' OAuth flows
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_oauth_linking"
down_revision: Union[str, None] = "005_add_google_oauth_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id and flow_type columns to oauth_states."""
    # Add user_id column (nullable - only set for link flows)
    op.add_column(
        "oauth_states",
        sa.Column("user_id", sa.UUID(), nullable=True),
    )

    # Add foreign key constraint for user_id
    op.create_foreign_key(
        "fk_oauth_states_user_id",
        "oauth_states",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Add flow_type column with default 'login'
    op.add_column(
        "oauth_states",
        sa.Column(
            "flow_type",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'login'"),
        ),
    )

    # Add index on user_id for efficient lookups
    op.create_index(
        "idx_oauth_states_user_id",
        "oauth_states",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove user_id and flow_type columns from oauth_states."""
    # Drop index on user_id
    op.drop_index("idx_oauth_states_user_id", table_name="oauth_states")

    # Drop foreign key constraint
    op.drop_constraint(
        "fk_oauth_states_user_id",
        "oauth_states",
        type_="foreignkey",
    )

    # Drop user_id column
    op.drop_column("oauth_states", "user_id")

    # Drop flow_type column
    op.drop_column("oauth_states", "flow_type")
