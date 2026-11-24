"""Allow re-encrypting a signed clinical note during a key rotation (runbook).

A signed note stays locked: any change is refused, as before. The only exception is the key
rotation command (python -m app.rotate_key), which sets app.key_rotation = 'on' for its own
transaction and changes nothing but content_encrypted (the same text, encrypted with the new
key; the command checks that the text is identical before writing).

Revision ID: 0015
Revises: 0014
"""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

LOCKED = """
    CREATE OR REPLACE FUNCTION clinical_notes_protect_signed() RETURNS trigger AS $$
    BEGIN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'clinical notes are never deleted';
        END IF;
        IF OLD.signed_at IS NOT NULL THEN
            IF current_setting('app.key_rotation', true) = 'on'
               AND (NEW.id, NEW.appointment_id, NEW.therapist_id, NEW.version,
                    NEW.amends_note_id, NEW.signed_at, NEW.created_at, NEW.updated_at)
                   IS NOT DISTINCT FROM
                   (OLD.id, OLD.appointment_id, OLD.therapist_id, OLD.version,
                    OLD.amends_note_id, OLD.signed_at, OLD.created_at, OLD.updated_at) THEN
                RETURN NEW;  -- key rotation: only the encryption changes
            END IF;
            RAISE EXCEPTION 'a signed clinical note cannot be changed; add an amendment';
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
"""

ORIGINAL = """
    CREATE OR REPLACE FUNCTION clinical_notes_protect_signed() RETURNS trigger AS $$
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
"""


def upgrade() -> None:
    op.execute(LOCKED)


def downgrade() -> None:
    op.execute(ORIGINAL)
