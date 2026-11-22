"""Desk payments: balance paid at the clinic by cash, debit or credit (B-FRD-05).

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-23 09:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_payments_type", "payments", type_="check")
    op.create_check_constraint(
        "ck_payments_type", "payments", "type IN ('deposit', 'refund', 'balance')"
    )
    op.drop_constraint("ck_payments_method", "payments", type_="check")
    op.create_check_constraint(
        "ck_payments_method", "payments", "method IN ('stripe', 'cash', 'debit', 'credit')"
    )
    op.add_column(
        "payments",
        sa.Column("recorded_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payments", "recorded_by")
    op.execute("DELETE FROM payments WHERE type = 'balance' OR method = 'credit'")
    op.drop_constraint("ck_payments_method", "payments", type_="check")
    op.create_check_constraint(
        "ck_payments_method", "payments", "method IN ('stripe', 'cash', 'debit')"
    )
    op.drop_constraint("ck_payments_type", "payments", type_="check")
    op.create_check_constraint("ck_payments_type", "payments", "type IN ('deposit', 'refund')")
