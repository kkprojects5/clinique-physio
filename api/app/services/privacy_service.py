"""Law 25: privacy requests and the confidentiality incident register (B-ADM-04, B-ADM-05).

Requests
- A patient asks, from their account, to see (access), correct or delete their information.
- The clinic must answer within 30 days. The law's exact count is debated (calendar or working
  days); the application uses 30 calendar days, the shorter one, and shows late requests.
- An access request can be answered with an export of the personal information kept about the
  patient. Clinical notes are NOT in it: the administrator never reads them (BR-6); the
  treating physiotherapist gives the clinical record separately.
- A deletion request closes the account and erases contact details at once. Health records
  (appointments, notes, exercise programs) are kept until the end of the retention period
  (5 years after the last visit, fictional rule of the professional order), with the reason
  written in the request; a patient without any health record is fully anonymized.
- The patient is told by email when the request is answered.

Incidents
- Every confidentiality incident is recorded; entries are never deleted (database trigger)
  and kept at least 5 years. An incident with a risk of serious injury must be notified to
  the Commission d'accès à l'information (CAI) and to the people concerned: the register
  shows which notifications are still missing.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.security import hash_password, new_refresh_token
from app.models import (
    Appointment,
    Consent,
    Incident,
    Patient,
    Payment,
    PrivacyRequest,
    Program,
    RefreshToken,
    User,
)
from app.services import audit_service
from app.services.password_reset_service import Email
from app.services.slots import CLINIC_TZ

ANSWER_DAYS = 30
RETENTION_YEARS = 5
OPEN_STATUSES = ("received", "in_progress")

ANSWERED_SUBJECT = {
    "fr": "Réponse à votre demande sur vos renseignements personnels",
    "en": "Answer to your request about your personal information",
}
ANSWERED_BODY = {
    "fr": "La clinique a répondu à votre demande ({type}). Réponse : {outcome}\n\n"
    "Vous pouvez la consulter dans « Mes données » sur le site. Si vous n'êtes pas satisfait, "
    "vous pouvez demander une révision à la Commission d'accès à l'information du Québec.",
    "en": "The clinic answered your request ({type}). Answer: {outcome}\n\n"
    'You can see it in "My data" on the website. If you are not satisfied, you can ask the '
    "Commission d'accès à l'information du Québec to review it.",
}
TYPE_NAMES = {
    "fr": {"access": "accès", "correction": "correction", "deletion": "suppression"},
    "en": {"access": "access", "correction": "correction", "deletion": "deletion"},
}


class PrivacyError(Exception):
    def __init__(self, detail: str, status_code: int = 409) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


# --- Patient side -----------------------------------------------------------------------------


def submit(
    db: Session, patient: Patient, kind: str, details: str | None, request: Request | None
) -> PrivacyRequest:
    """A new request. Only one open request of each type at a time."""
    already = db.scalar(
        select(PrivacyRequest.id).where(
            PrivacyRequest.patient_id == patient.id,
            PrivacyRequest.type == kind,
            PrivacyRequest.status.in_(OPEN_STATUSES),
        )
    )
    if already:
        raise PrivacyError("You already have an open request of this type.")
    now = datetime.now(UTC)
    item = PrivacyRequest(
        patient_id=patient.id,
        type=kind,
        details=(details or "").strip() or None,
        requested_at=now,
        due_at=now + timedelta(days=ANSWER_DAYS),
    )
    db.add(item)
    db.flush()
    audit_service.log(
        db, patient.user_id, "create", "privacy_request", item.id, patient.id, request
    )
    db.commit()
    return item


def my_requests(db: Session, patient: Patient) -> list[PrivacyRequest]:
    return list(
        db.scalars(
            select(PrivacyRequest)
            .where(PrivacyRequest.patient_id == patient.id)
            .order_by(PrivacyRequest.requested_at.desc())
        )
    )


# --- Administrator side -----------------------------------------------------------------------


@dataclass
class RequestView:
    item: PrivacyRequest
    patient: Patient
    email: str

    @property
    def overdue(self) -> bool:
        return self.item.status in OPEN_STATUSES and self.item.due_at < datetime.now(UTC)


def list_requests(db: Session) -> list[RequestView]:
    """Open requests first (oldest deadline first), then answered ones."""
    rows = db.execute(
        select(PrivacyRequest, Patient, User.email)
        .join(Patient, Patient.id == PrivacyRequest.patient_id)
        .join(User, User.id == Patient.user_id)
        .order_by(PrivacyRequest.status.in_(OPEN_STATUSES).desc(), PrivacyRequest.due_at)
    ).all()
    return [RequestView(r.PrivacyRequest, r.Patient, r.email) for r in rows]


def _get(db: Session, request_id: uuid.UUID) -> PrivacyRequest:
    item = db.get(PrivacyRequest, request_id)
    if item is None:
        raise PrivacyError("Not found.", 404)
    return item


def _answered_email(db: Session, item: PrivacyRequest) -> Email | None:
    patient = db.get(Patient, item.patient_id)
    user = db.get(User, patient.user_id)
    lang = user.language
    if item.type == "deletion" and item.status == "completed":
        return None  # the address was just erased; the answer stays visible to the clinic
    body = ANSWERED_BODY[lang].format(type=TYPE_NAMES[lang][item.type], outcome=item.outcome)
    return Email(user.email, ANSWERED_SUBJECT[lang], body)


def update_request(
    db: Session,
    admin: User,
    request_id: uuid.UUID,
    status: str,
    outcome: str | None,
    request: Request | None,
) -> tuple[PrivacyRequest, Email | None]:
    """Move a request forward. Completing or refusing needs a written answer for the person."""
    item = _get(db, request_id)
    if item.status not in OPEN_STATUSES:
        raise PrivacyError("This request is already answered.")
    if status in ("completed", "refused") and not (outcome or "").strip():
        raise PrivacyError("Write the answer given to the person.", 422)
    if status == "completed" and item.type == "deletion":
        raise PrivacyError("Use the erase action to complete a deletion request.", 422)
    item.status = status
    item.handled_by = admin.id
    if outcome:
        item.outcome = outcome.strip()
    if status in ("completed", "refused"):
        item.completed_at = datetime.now(UTC)
    audit_service.log(db, admin.id, status, "privacy_request", item.id, item.patient_id, request)
    db.commit()
    email = _answered_email(db, item) if status in ("completed", "refused") else None
    return item, email


def export(db: Session, admin: User, request_id: uuid.UUID, request: Request | None) -> dict:
    """Personal information kept about the patient, for an access request (no clinical notes)."""
    item = _get(db, request_id)
    if item.type != "access":
        raise PrivacyError("Only access requests have an export.", 422)
    patient = db.get(Patient, item.patient_id)
    user = db.get(User, patient.user_id)
    consents = db.scalars(select(Consent).where(Consent.user_id == user.id)).all()
    appointments = db.scalars(
        select(Appointment).where(Appointment.patient_id == patient.id).order_by(Appointment.during)
    ).all()
    payments = db.scalars(
        select(Payment).where(Payment.appointment_id.in_([a.id for a in appointments]))
    ).all()
    audit_service.log(db, admin.id, "export", "privacy_request", item.id, patient.id, request)
    db.commit()
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "note": "Clinical notes and exercise programs are given by the treating physiotherapist.",
        "account": {
            "email": user.email,
            "language": user.language,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        },
        "profile": {
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "date_of_birth": patient.date_of_birth.isoformat(),
            "phone": patient.phone,
            "emergency_contact_on_file": patient.emergency_contact_enc is not None,
        },
        "consents": [
            {
                "type": c.type,
                "version": c.version,
                "granted_at": c.granted_at.isoformat(),
                "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None,
            }
            for c in consents
        ],
        "appointments": [
            {
                "start": a.during.lower.astimezone(CLINIC_TZ).isoformat(),
                "status": a.status,
                "service_id": str(a.service_id),
                "therapist_id": str(a.therapist_id),
            }
            for a in appointments
        ],
        "payments": [
            {
                "type": p.type,
                "amount_cents": p.amount_cents,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
            }
            for p in payments
        ],
    }


def _last_visit(db: Session, patient_id: uuid.UUID) -> datetime | None:
    return db.scalar(
        select(func.max(func.lower(Appointment.during))).where(Appointment.patient_id == patient_id)
    )


def erase(
    db: Session, admin: User, request_id: uuid.UUID, request: Request | None
) -> PrivacyRequest:
    """Complete a deletion request: close the account and erase what the clinic may erase."""
    item = _get(db, request_id)
    if item.type != "deletion":
        raise PrivacyError("Only deletion requests can be erased.", 422)
    if item.status not in OPEN_STATUSES:
        raise PrivacyError("This request is already answered.")
    patient = db.get(Patient, item.patient_id)
    user = db.get(User, patient.user_id)
    now = datetime.now(UTC)

    # The account: closed, sessions ended, contact details erased, consents withdrawn.
    user.is_active = False
    user.email = f"erased-{user.id}@invalid.example"
    user.password_hash = hash_password(new_refresh_token())
    user.mfa_secret_enc = None
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.execute(
        update(Consent)
        .where(Consent.user_id == user.id, Consent.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    patient.phone = "—"
    patient.emergency_contact_enc = None

    last_visit = _last_visit(db, patient.id)
    has_program = db.scalar(select(Program.id).where(Program.patient_id == patient.id).limit(1))
    if last_visit is None and has_program is None:
        patient.first_name = "Anonymized"
        patient.last_name = "Patient"
        item.outcome = (
            "Account closed. No health record was kept, so all personal information was "
            "erased or anonymized."
        )
    else:
        keep_until = (last_visit or now).astimezone(CLINIC_TZ).date()
        keep_until = keep_until.replace(year=keep_until.year + RETENTION_YEARS)
        item.outcome = (
            "Account closed, contact details erased and consents withdrawn. The health record "
            f"(appointments, notes, exercise programs) is kept until {keep_until.isoformat()} "
            f"({RETENTION_YEARS} years after the last visit), as the professional order "
            "requires, then anonymized."
        )
    item.status = "completed"
    item.handled_by = admin.id
    item.completed_at = now
    audit_service.log(db, admin.id, "erase", "privacy_request", item.id, patient.id, request)
    db.commit()
    return item


# --- Incident register ------------------------------------------------------------------------


def to_notify(incident: Incident) -> list[str]:
    """Notifications still missing for an incident with a risk of serious injury."""
    if incident.risk_level != "serious":
        return []
    missing = []
    if incident.cai_notified_at is None:
        missing.append("cai")
    if incident.persons_notified_at is None:
        missing.append("persons")
    return missing


def list_incidents(db: Session) -> list[Incident]:
    return list(db.scalars(select(Incident).order_by(Incident.discovered_at.desc())))


def _check_dates(fields: dict, current: Incident | None = None) -> None:
    occurred = fields.get("occurred_at", current.occurred_at if current else None)
    discovered = fields.get("discovered_at", current.discovered_at if current else None)
    now = datetime.now(UTC)
    if occurred and discovered and discovered < occurred:
        raise PrivacyError("The discovery date cannot be before the incident.", 422)
    for name in ("occurred_at", "discovered_at", "cai_notified_at", "persons_notified_at"):
        value = fields.get(name)
        if value is not None and value > now + timedelta(minutes=5):
            raise PrivacyError("Dates cannot be in the future.", 422)


def record_incident(db: Session, admin: User, fields: dict, request: Request | None) -> Incident:
    _check_dates(fields)
    incident = Incident(**fields, recorded_by=admin.id)
    db.add(incident)
    db.flush()
    audit_service.log(db, admin.id, "create", "incident", incident.id, None, request)
    db.commit()
    return incident


def update_incident(
    db: Session, admin: User, incident_id: uuid.UUID, fields: dict, request: Request | None
) -> Incident:
    """Keep the entry up to date (measures, notifications). Entries are never deleted."""
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise PrivacyError("Not found.", 404)
    _check_dates(fields, incident)
    for name, value in fields.items():
        setattr(incident, name, value)
    incident.updated_at = datetime.now(UTC)
    audit_service.log(db, admin.id, "update", "incident", incident.id, None, request)
    db.commit()
    return incident
