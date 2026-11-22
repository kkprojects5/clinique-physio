"""Therapist photo on the team page (B-AVL-05).

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-23 18:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | Sequence[str] | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("therapists", sa.Column("photo", sa.LargeBinary(), nullable=True))
    op.add_column(
        "therapists", sa.Column("photo_updated_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("therapists", "photo_updated_at")
    op.drop_column("therapists", "photo")
