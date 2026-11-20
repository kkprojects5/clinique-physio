"""Law 25: privacy requests and confidentiality incident register (B-ADM-04, B-ADM-05).

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-20 01:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "privacy_requests",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("patient_id", sa.UUID(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'received'"), nullable=False),
        sa.Column("requested_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("due_at", TS, nullable=False),
        sa.Column("completed_at", TS, nullable=True),
        sa.Column("handled_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.CheckConstraint("type IN ('access', 'correction', 'deletion')", name="ck_privacy_type"),
        sa.CheckConstraint(
            "status IN ('received', 'in_progress', 'completed', 'refused')",
            name="ck_privacy_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_privacy_requests_patient_id", "privacy_requests", ["patient_id"])
    op.create_table(
        "incident_register",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("occurred_at", TS, nullable=False),
        sa.Column("discovered_at", TS, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("data_categories", sa.Text(), nullable=False),
        sa.Column("people_affected", sa.Integer(), nullable=True),
        sa.Column("risk_level", sa.Text(), nullable=False),
        sa.Column("measures", sa.Text(), nullable=False),
        sa.Column("cai_notified_at", TS, nullable=True),
        sa.Column("persons_notified_at", TS, nullable=True),
        sa.Column("recorded_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("risk_level IN ('low', 'serious')", name="ck_incident_risk"),
        sa.CheckConstraint("discovered_at >= occurred_at", name="ck_incident_dates"),
        sa.PrimaryKeyConstraint("id"),
    )
    # The register is kept at least 5 years: an entry can never be deleted (Law 25).
    op.execute(
        """
        CREATE FUNCTION incident_register_no_delete() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'incident register entries cannot be deleted (Law 25)';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER incident_register_no_delete BEFORE DELETE ON incident_register
            FOR EACH ROW EXECUTE FUNCTION incident_register_no_delete();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS incident_register_no_delete ON incident_register")
    op.execute("DROP FUNCTION IF EXISTS incident_register_no_delete()")
    op.drop_table("incident_register")
    op.drop_index("ix_privacy_requests_patient_id", table_name="privacy_requests")
    op.drop_table("privacy_requests")
