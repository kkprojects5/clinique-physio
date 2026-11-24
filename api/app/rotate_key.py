"""Re-encrypt every encrypted field with the first key of FIELD_ENCRYPTION_KEY (runbook).

    1. FIELD_ENCRYPTION_KEY="new-key,old-key"   (new key first; both can read)
    2. cd api && python -m app.rotate_key        (re-encrypts with the new key)
    3. FIELD_ENCRYPTION_KEY="new-key"           (the old key can now be removed)

One transaction: either every value is re-encrypted, or none is. Each value is decrypted
again after re-encryption and compared with the original text before it is written, so the
content can never change. Running it twice does no harm. The run is recorded in the audit log.
Signed clinical notes stay locked for everything else (migration 0015).
"""

import sys

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core import crypto
from app.db.session import SessionLocal
from app.models import ClinicalNote, Patient, User
from app.services import audit_service

# (model, encrypted column) for every field encrypted with crypto.encrypt.
FIELDS = (
    (User, "mfa_secret_enc"),
    (Patient, "emergency_contact_enc"),
    (ClinicalNote, "content_encrypted"),
)


class RotationError(Exception):
    pass


def rotate_all(db: Session) -> dict[str, int]:
    """Re-encrypt every stored value with the first key. The caller commits."""
    db.execute(text("SET LOCAL app.key_rotation = 'on'"))
    counts: dict[str, int] = {}
    for model, column in FIELDS:
        attribute = getattr(model, column)
        rows = db.scalars(select(model).where(attribute.is_not(None))).all()
        for row in rows:
            old = getattr(row, column)
            new = crypto.rotate(old)
            if crypto.decrypt(new) != crypto.decrypt(old):
                raise RotationError(f"{model.__tablename__} {row.id}: text changed")
            setattr(row, column, new)
        counts[f"{model.__tablename__}.{column}"] = len(rows)
    audit_service.log(db, None, "key_rotation", "encryption_key")
    db.flush()
    return counts


def main() -> None:
    if len(crypto.keys()) < 2:
        print("Tip: put the new key first and keep the old one: FIELD_ENCRYPTION_KEY=new,old")
    with SessionLocal() as db:
        try:
            counts = rotate_all(db)
            db.commit()
        except Exception as error:  # nothing is written: the transaction is rolled back
            db.rollback()
            sys.exit(f"Key rotation failed, nothing was changed: {error}")
    for name, count in counts.items():
        print(f"{name}: {count} re-encrypted")
    print("Done. You can now remove the old key from FIELD_ENCRYPTION_KEY.")


if __name__ == "__main__":
    main()
