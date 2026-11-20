"""Clinic administration (B-ADM-01 services and staff, B-ADM-03 audit log viewer).

- Only an administrator with a two-factor session can use these functions (router).
- Services are never deleted (past appointments point to them): they are deactivated.
- A new staff member gets an account without a usable password and an email with a one-time
  link (72 hours) to choose one; at the first login they set up their 6-digit code (MFA).
  The administrator never sees or chooses another person's password.
- Only therapist and front-desk accounts can be created here: a new administrator is created
  by the clinic owner outside the application (no privilege escalation through the API).
- Deactivating an account closes its sessions at once and hides a therapist from booking.
- Every change, and every reading of the audit log, is itself written to the audit log.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from fastapi import Request
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, new_refresh_token
from app.models import (
    ACTIVE_STATUSES,
    Appointment,
    AuditLog,
    Patient,
    RefreshToken,
    Service,
    Therapist,
    TherapistService,
    User,
)
from app.services import audit_service
from app.services.email import send_email
from app.services.password_reset_service import Email, new_password_link
from app.services.slots import CLINIC_TZ

CREATABLE_ROLES = ("therapist", "front_desk")
# More different patients than this read by one person within one hour is highlighted.
UNUSUAL_PATIENTS_PER_HOUR = 10
STAFF_ROLES = ("therapist", "front_desk", "admin")
AUDIT_PAGE_MAX = 100

INVITE_SUBJECT = {
    "fr": "Votre compte à la Clinique Physio Mont-Royal",
    "en": "Your account at Clinique Physio Mont-Royal",
}
INVITE_BODY = {
    "fr": "Un compte {role} a été créé pour vous. Choisissez votre mot de passe avec ce lien "
    "(valide {hours} heures, une seule fois) : {link}\n\nÀ la première connexion, vous "
    "configurerez aussi votre code à 6 chiffres (application d'authentification).",
    "en": "A {role} account was created for you. Choose your password with this link "
    "(valid {hours} hours, once only): {link}\n\nAt your first login you will also set up "
    "your 6-digit code (authenticator app).",
}
ROLE_NAMES = {
    "fr": {"therapist": "physiothérapeute", "front_desk": "accueil"},
    "en": {"therapist": "physiotherapist", "front_desk": "front desk"},
}


class AdminError(Exception):
    status_code = 409

    def __init__(self, detail: str, status_code: int | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code


def _not_found() -> AdminError:
    return AdminError("Not found.", 404)


# --- Services --------------------------------------------------------------------------------


def _service_therapists(db: Session, service_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(TherapistService.therapist_id).where(TherapistService.service_id == service_id)
        )
    )


def list_services(db: Session) -> list[tuple[Service, list[uuid.UUID]]]:
    """All services, inactive ones included, with the therapists who give them."""
    services = db.scalars(select(Service).order_by(Service.is_active.desc(), Service.name_fr))
    return [(s, _service_therapists(db, s.id)) for s in services]


def _set_therapists(db: Session, service: Service, therapist_ids: list[uuid.UUID]) -> None:
    unique = set(therapist_ids)
    found = set(db.scalars(select(Therapist.id).where(Therapist.id.in_(unique))))
    if found != unique:
        raise AdminError("Unknown therapist.", 422)
    db.execute(delete(TherapistService).where(TherapistService.service_id == service.id))
    for therapist_id in unique:
        db.add(TherapistService(therapist_id=therapist_id, service_id=service.id))


def _check_money(price_cents: int, deposit_cents: int) -> None:
    if deposit_cents > price_cents:
        raise AdminError("The deposit cannot be more than the price.", 422)


def create_service(
    db: Session, admin: User, fields: dict, therapist_ids: list[uuid.UUID], request: Request
) -> tuple[Service, list[uuid.UUID]]:
    _check_money(fields["price_cents"], fields["deposit_cents"])
    service = Service(**fields)
    db.add(service)
    db.flush()
    try:
        _set_therapists(db, service, therapist_ids)
    except AdminError:
        db.rollback()  # nothing is saved, not even the service
        raise
    audit_service.log(db, admin.id, "create", "service", service.id, None, request)
    db.commit()
    return service, _service_therapists(db, service.id)


def update_service(
    db: Session,
    admin: User,
    service_id: uuid.UUID,
    fields: dict,
    therapist_ids: list[uuid.UUID] | None,
    request: Request,
) -> tuple[Service, list[uuid.UUID]]:
    """Change only the fields given. Deactivating stops new bookings; booked ones stay."""
    service = db.get(Service, service_id)
    if service is None:
        raise _not_found()
    try:
        for name, value in fields.items():
            setattr(service, name, value)
        _check_money(service.price_cents, service.deposit_cents)
        if therapist_ids is not None:
            _set_therapists(db, service, therapist_ids)
    except AdminError:
        db.rollback()  # all or nothing
        raise
    action = "update"
    if fields.get("is_active") is False:
        action = "deactivate"
    elif fields.get("is_active") is True:
        action = "activate"
    audit_service.log(db, admin.id, action, "service", service.id, None, request)
    db.commit()
    return service, _service_therapists(db, service.id)


# --- Staff -----------------------------------------------------------------------------------


@dataclass
class StaffView:
    user: User
    therapist: Therapist | None
    future_appointments: int


def _future_count(db: Session, therapist: Therapist | None) -> int:
    if therapist is None:
        return 0
    return db.scalar(
        select(func.count())
        .select_from(Appointment)
        .where(
            Appointment.therapist_id == therapist.id,
            Appointment.status.in_(ACTIVE_STATUSES),
            func.lower(Appointment.during) > datetime.now(UTC),
        )
    )


def _view(db: Session, user: User) -> StaffView:
    therapist = db.scalar(select(Therapist).where(Therapist.user_id == user.id))
    return StaffView(user, therapist, _future_count(db, therapist))


def list_staff(db: Session) -> list[StaffView]:
    users = db.scalars(
        select(User).where(User.role.in_(STAFF_ROLES)).order_by(User.role, User.email)
    )
    return [_view(db, u) for u in users]


def _invite_email(db: Session, user: User) -> Email:
    link = new_password_link(db, user, settings.staff_invite_hours * 60)
    body = INVITE_BODY[user.language].format(
        role=ROLE_NAMES[user.language][user.role], hours=settings.staff_invite_hours, link=link
    )
    return Email(user.email, INVITE_SUBJECT[user.language], body)


def create_staff(
    db: Session,
    admin: User,
    email: str,
    role: str,
    language: str,
    therapist_fields: dict | None,
    request: Request,
) -> tuple[StaffView, Email]:
    """Create a therapist or front-desk account and its invitation email (sent by the caller)."""
    if role not in CREATABLE_ROLES:
        raise AdminError("Only therapist and front-desk accounts can be created.", 422)
    email = email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise AdminError("An account already uses this email.")
    if role == "therapist":
        if not therapist_fields:
            raise AdminError("A therapist needs a first name, last name and licence number.", 422)
        licence = therapist_fields["licence_number"]
        if db.scalar(select(Therapist.id).where(Therapist.licence_number == licence)):
            raise AdminError("This licence number is already used.")
    user = User(
        email=email,
        # No usable password until the invitation link is used: a random value nobody knows.
        password_hash=hash_password(new_refresh_token()),
        role=role,
        language=language,
    )
    db.add(user)
    db.flush()
    if role == "therapist":
        db.add(Therapist(user_id=user.id, **therapist_fields))
    audit_service.log(db, admin.id, "create", "user", user.id, None, request)
    invitation = _invite_email(db, user)
    db.commit()
    return _view(db, user), invitation


def _staff_user(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None or user.role not in STAFF_ROLES:
        raise _not_found()
    return user


def set_active(
    db: Session, admin: User, user_id: uuid.UUID, active: bool, request: Request
) -> StaffView:
    """Activate or deactivate a staff account. Deactivating closes all its sessions at once."""
    user = _staff_user(db, user_id)
    if user.id == admin.id:
        raise AdminError("You cannot deactivate your own account.")
    if user.role == "admin":
        raise AdminError("Administrator accounts are managed by the clinic owner.")
    user.is_active = active
    if not active:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
    action = "activate" if active else "deactivate"
    audit_service.log(db, admin.id, action, "user", user.id, None, request)
    db.commit()
    return _view(db, user)


def resend_invitation(db: Session, admin: User, user_id: uuid.UUID, request: Request) -> Email:
    """A new password link (the previous one stops working), e.g. if the first one expired."""
    user = _staff_user(db, user_id)
    if user.role == "admin" or not user.is_active:
        raise AdminError("No invitation for this account.")
    audit_service.log(db, admin.id, "invite", "user", user.id, None, request)
    invitation = _invite_email(db, user)
    db.commit()
    return invitation


def send(invitation: Email) -> None:
    send_email(invitation.to, invitation.subject, invitation.body)


# --- Audit log -------------------------------------------------------------------------------


@dataclass
class AuditFilter:
    date_from: date | None = None
    date_to: date | None = None
    action: str | None = None
    resource_type: str | None = None
    actor_email: str | None = None
    patient_id: uuid.UUID | None = None
    before_id: int | None = None  # next page: entries older than this one
    limit: int = 50


@dataclass
class AuditRow:
    entry: AuditLog
    actor_email: str | None
    actor_role: str | None
    patient_name: str | None
    unusual: bool = False


def _busy_hours(db: Session, rows: list) -> set[tuple[uuid.UUID, datetime]]:
    """(actor, hour) pairs where the actor read more different patients than the limit."""
    actors = {r.AuditLog.actor_id for r in rows if r.AuditLog.actor_id}
    if not actors:
        return set()
    hour = func.date_trunc("hour", AuditLog.created_at)
    busy = db.execute(
        select(AuditLog.actor_id, hour)
        .where(
            AuditLog.actor_id.in_(actors),
            AuditLog.action == "read",
            AuditLog.patient_id.is_not(None),
        )
        .group_by(AuditLog.actor_id, hour)
        .having(func.count(func.distinct(AuditLog.patient_id)) > UNUSUAL_PATIENTS_PER_HOUR)
    ).all()
    return {(actor, at) for actor, at in busy}


def _is_unusual(entry: AuditLog, busy: set[tuple[uuid.UUID, datetime]]) -> bool:
    """A refused access, or a patient read during an hour with too many different patients."""
    if entry.action == "access_denied":
        return True
    if entry.action != "read" or entry.patient_id is None:
        return False
    hour = entry.created_at.replace(minute=0, second=0, microsecond=0)
    return (entry.actor_id, hour) in busy


def _local_midnight_utc(day: date) -> datetime:
    return datetime.combine(day, time.min, CLINIC_TZ).astimezone(UTC)


def read_audit(
    db: Session, admin: User, where: AuditFilter, request: Request
) -> tuple[list[AuditRow], int | None]:
    """Entries newest first, and the id to ask for the next page (None on the last page).

    Days are in Montréal time. Refused accesses, and reads by someone who opened more than
    UNUSUAL_PATIENTS_PER_HOUR different patients in the same hour, are marked unusual.
    Reading the log is itself logged (who watches the watchers).
    """
    query = (
        select(AuditLog, User.email, User.role, Patient.first_name, Patient.last_name)
        .outerjoin(User, User.id == AuditLog.actor_id)
        .outerjoin(Patient, Patient.id == AuditLog.patient_id)
    )
    if where.date_from:
        query = query.where(AuditLog.created_at >= _local_midnight_utc(where.date_from))
    if where.date_to:
        end = _local_midnight_utc(where.date_to + timedelta(days=1))
        query = query.where(AuditLog.created_at < end)
    if where.action:
        query = query.where(AuditLog.action == where.action)
    if where.resource_type:
        query = query.where(AuditLog.resource_type == where.resource_type)
    if where.actor_email:
        query = query.where(User.email == where.actor_email.strip().lower())
    if where.patient_id:
        query = query.where(AuditLog.patient_id == where.patient_id)
    if where.before_id:
        query = query.where(AuditLog.id < where.before_id)
    limit = max(1, min(where.limit, AUDIT_PAGE_MAX))
    rows = db.execute(query.order_by(AuditLog.id.desc()).limit(limit + 1)).all()
    more = len(rows) > limit
    rows = rows[:limit]

    busy = _busy_hours(db, rows)
    result = [
        AuditRow(
            entry=row.AuditLog,
            actor_email=row.email,
            actor_role=row.role,
            patient_name=f"{row.first_name} {row.last_name}" if row.first_name else None,
            unusual=_is_unusual(row.AuditLog, busy),
        )
        for row in rows
    ]
    audit_service.log(db, admin.id, "read", "audit_log", None, where.patient_id, request)
    db.commit()
    return result, (result[-1].entry.id if more and result else None)
