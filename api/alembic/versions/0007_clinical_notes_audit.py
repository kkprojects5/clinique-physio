"""Clinical notes and append-only audit log (B-CLN-02 to 05).

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-09 11:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clinical_notes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("therapist_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("amends_note_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"]),
        sa.ForeignKeyConstraint(["therapist_id"], ["therapists.id"]),
        sa.ForeignKeyConstraint(["amends_note_id"], ["clinical_notes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_clinical_notes_appointment_id", "clinical_notes", ["appointment_id"], unique=False
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("client_app", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"], unique=False)
    op.create_index("ix_audit_logs_patient_id", "audit_logs", ["patient_id"], unique=False)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)

    # Append-only: the database refuses any change or deletion of audit rows and clinical notes,
    # even from the application. Notes may only change while they are drafts.
    op.execute(
        """
        CREATE FUNCTION audit_logs_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs rows can only be added';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER audit_logs_no_change
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION audit_logs_append_only();

        CREATE FUNCTION clinical_notes_protect_signed() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'clinical notes are never deleted';
            END IF;
            IF OLD.signed_at IS NOT NULL THEN
                RAISE EXCEPTION 'a signed clinical note cannot be changed; add an amendment';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER clinical_notes_signed_locked
        BEFORE UPDATE OR DELETE ON clinical_notes
        FOR EACH ROW EXECUTE FUNCTION clinical_notes_protect_signed();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER clinical_notes_signed_locked ON clinical_notes")
    op.execute("DROP FUNCTION clinical_notes_protect_signed()")
    op.execute("DROP TRIGGER audit_logs_no_change ON audit_logs")
    op.execute("DROP FUNCTION audit_logs_append_only()")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_patient_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_clinical_notes_appointment_id", table_name="clinical_notes")
    op.drop_table("clinical_notes")
