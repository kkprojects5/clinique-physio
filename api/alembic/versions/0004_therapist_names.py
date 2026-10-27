"""Therapists: first and last name, needed for the public team page (B-AVL-05).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-26 20:55:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A temporary default fills existing rows, then it is removed so new rows must give a name.
    for column in ("first_name", "last_name"):
        op.add_column(
            "therapists",
            sa.Column(column, sa.Text(), nullable=False, server_default=sa.text("''")),
        )
        op.alter_column("therapists", column, server_default=None)


def downgrade() -> None:
    op.drop_column("therapists", "last_name")
    op.drop_column("therapists", "first_name")
