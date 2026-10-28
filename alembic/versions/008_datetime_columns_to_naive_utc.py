"""Convert datetime columns to TIMESTAMP WITHOUT TIME ZONE (naive UTC).

Revision ID: 008_naive_utc_datetimes
Revises: 007_drop_genres_table
Create Date: 2026-10-28

ADR-0010: every datetime column stores naive UTC. Migrations 001, 002 and 005
created ``timestamptz`` columns; this converts them with
``USING col AT TIME ZONE 'UTC'`` (UTC wall-clock time, independent of the
session time zone) and moves column defaults to ``timezone('utc', now())``.
Columns that are already ``timestamp without time zone`` are skipped, so the
migration is safe on a database that was converted by hand.

Run it when nobody is importing: ALTER COLUMN TYPE rewrites the table under an
ACCESS EXCLUSIVE lock. Downgrade restores ``timestamptz`` and
``CURRENT_TIMESTAMP`` defaults.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008_naive_utc_datetimes"
down_revision: Union[str, None] = "007_drop_genres_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, column, has_server_default)
COLUMNS = [
    ("users", "created_at", True),
    ("users", "updated_at", True),
    ("movies", "created_at", True),
    ("movies", "updated_at", True),
    ("rankings", "created_at", True),
    ("rankings", "updated_at", True),
    ("rankings", "rated_at", True),
    ("oauth_states", "created_at", True),
    ("oauth_states", "expires_at", False),
]


def _data_type(table: str, column: str) -> str:
    """Return the information_schema data_type of a column."""
    bind = op.get_bind()
    return bind.execute(
        sa.text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_schema = current_schema() "
            "AND table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).scalar_one()


def _convert(
    table: str,
    column: str,
    has_default: bool,
    *,
    from_type: str,
    to_type: str,
    new_default: str,
) -> None:
    if _data_type(table, column) != from_type:
        return  # already in the target type
    if has_default:
        # Drop first so PostgreSQL does not have to cast the old default.
        op.alter_column(table, column, server_default=None)
    op.execute(
        f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
        f"TYPE {to_type} USING \"{column}\" AT TIME ZONE 'UTC'"
    )
    if has_default:
        op.alter_column(table, column, server_default=sa.text(new_default))


def upgrade() -> None:
    """Convert timestamptz columns to naive UTC timestamps."""
    for table, column, has_default in COLUMNS:
        _convert(
            table,
            column,
            has_default,
            from_type="timestamp with time zone",
            to_type="TIMESTAMP WITHOUT TIME ZONE",
            new_default="timezone('utc', now())",
        )


def downgrade() -> None:
    """Restore timestamptz columns and CURRENT_TIMESTAMP defaults."""
    for table, column, has_default in COLUMNS:
        _convert(
            table,
            column,
            has_default,
            from_type="timestamp without time zone",
            to_type="TIMESTAMP WITH TIME ZONE",
            new_default="CURRENT_TIMESTAMP",
        )
