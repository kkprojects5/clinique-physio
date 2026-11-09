"""Payments and Stripe webhook events (B-BKG-04, B-BKG-06).

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-09 13:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("appointment_id", sa.UUID(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("method", sa.Text(), server_default=sa.text("'stripe'"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("stripe_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("method IN ('stripe', 'cash', 'debit')", name="ck_payments_method"),
        sa.CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed')", name="ck_payments_status"
        ),
        sa.CheckConstraint("type IN ('deposit', 'refund')", name="ck_payments_type"),
        sa.CheckConstraint("amount_cents > 0", name="ck_payments_amount"),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_id"),
    )
    op.create_index(
        op.f("ix_payments_appointment_id"), "payments", ["appointment_id"], unique=False
    )
    op.create_table(
        "payment_events",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("payment_id", sa.UUID(), nullable=True),
        sa.Column("stripe_event_id", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_event_id"),
    )


def downgrade() -> None:
    op.drop_table("payment_events")
    op.drop_index(op.f("ix_payments_appointment_id"), table_name="payments")
    op.drop_table("payments")
