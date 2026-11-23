"""Consent management (Law 25): the patient sees and changes what they agreed to.

- privacy_policy: required to have an account. It cannot be withdrawn while the account is
  open; to stop all processing, the patient asks for deletion (B-ADM-04). When the clinic
  publishes a new version of the policy, the patient accepts it here; each version accepted
  is kept with its date, so the clinic can prove what was agreed to and when.
- electronic_comms: optional. Non-essential messages from the clinic (reminders, news) are
  sent only while it is given. Messages needed for a service the patient asked for (booking
  confirmations, password reset, answers to privacy requests) do not depend on it.

Withdrawing keeps the row with its withdrawal date; giving it again adds a new row, so the
full history stays available for an access request. Every change is in the audit log.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Consent, Patient, User
from app.services import audit_service

TYPES = ("privacy_policy", "electronic_comms")


@dataclass
class ConsentState:
    type: str
    given: bool
    version: str | None
    granted_at: datetime | None
    revoked_at: datetime | None
    current_version: str

    @property
    def up_to_date(self) -> bool:
        return self.given and self.version == self.current_version


def _latest(db: Session, user: User, kind: str) -> Consent | None:
    return db.scalar(
        select(Consent)
        .where(Consent.user_id == user.id, Consent.type == kind)
        .order_by(Consent.revoked_at.is_(None).desc(), Consent.granted_at.desc())
        .limit(1)
    )


def _state(db: Session, user: User, kind: str) -> ConsentState:
    latest = _latest(db, user, kind)
    return ConsentState(
        type=kind,
        given=latest is not None and latest.revoked_at is None,
        version=latest.version if latest else None,
        granted_at=latest.granted_at if latest else None,
        revoked_at=latest.revoked_at if latest else None,
        current_version=settings.privacy_policy_version,
    )


def my_consents(db: Session, user: User) -> list[ConsentState]:
    return [_state(db, user, kind) for kind in TYPES]


def history(db: Session, user: User) -> list[Consent]:
    return list(
        db.scalars(select(Consent).where(Consent.user_id == user.id).order_by(Consent.granted_at))
    )


def set_electronic_comms(
    db: Session, user: User, patient: Patient, given: bool, request: Request | None
) -> ConsentState:
    """Give or withdraw the optional consent. Doing what is already done changes nothing."""
    latest = _latest(db, user, "electronic_comms")
    active = latest is not None and latest.revoked_at is None
    if given and not active:
        db.add(
            Consent(
                user_id=user.id,
                type="electronic_comms",
                version=settings.privacy_policy_version,
                granted_at=datetime.now(UTC),
            )
        )
    elif not given and active:
        latest.revoked_at = datetime.now(UTC)
    else:
        return _state(db, user, "electronic_comms")
    audit_service.log(
        db,
        user.id,
        "consent_given" if given else "consent_withdrawn",
        "consent",
        None,
        patient.id,
        request,
    )
    db.commit()
    return _state(db, user, "electronic_comms")


def accept_policy(
    db: Session, user: User, patient: Patient, request: Request | None
) -> ConsentState:
    """Accept the current version of the privacy policy (after it changed)."""
    state = _state(db, user, "privacy_policy")
    if state.up_to_date:
        return state
    db.add(
        Consent(
            user_id=user.id,
            type="privacy_policy",
            version=settings.privacy_policy_version,
            granted_at=datetime.now(UTC),
        )
    )
    audit_service.log(db, user.id, "consent_given", "consent", None, patient.id, request)
    db.commit()
    return _state(db, user, "privacy_policy")


def wants_electronic_comms(db: Session, user: User) -> bool:
    """For non-essential messages (reminders, news): send only when this is True."""
    return _state(db, user, "electronic_comms").given
