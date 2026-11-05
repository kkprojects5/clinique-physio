"""Booking lifecycle: 'expired' status and appointment status history (B-BKG-03, B-BKG-05).

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-05 15:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_STATUSES = (
    "status IN ('held', 'pending_payment', 'confirmed', 'checked_in', 'completed',"
    " 'cancelled_by_patient', 'cancelled_by_clinic', 'no_show')"
)
NEW_STATUSES = (
    "status IN ('held', 'pending_payment', 'confirmed', 'checked_in', 'completed',"
    " 'cancelled_by_patient', 'cancelled_by_clinic', 'no_show', 'expired')"
)


def upgrade() -> None:
    op.drop_constraint("ck_appointments_status", "appointments", type_="check")
    op.create_check_constraint("ck_appointments_status", "appointments", NEW_STATUSES)

    op.create_table(
        "appointment_status_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.Text(), nullable=True),
        sa.Column("to_status", sa.Text(), nullable=False),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"]),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_appointment_status_history_appointment_id",
        "appointment_status_history",
        ["appointment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_appointment_status_history_appointment_id", table_name="appointment_status_history"
    )
    op.drop_table("appointment_status_history")
    op.execute("UPDATE appointments SET status = 'cancelled_by_clinic' WHERE status = 'expired'")
    op.drop_constraint("ck_appointments_status", "appointments", type_="check")
    op.create_check_constraint("ck_appointments_status", "appointments", OLD_STATUSES)
