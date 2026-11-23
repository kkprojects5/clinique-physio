"""Law 25 (B-ADM-04, B-ADM-05): patients' privacy requests and the incident register."""

import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from app.core import rate_limit
from app.core.rate_limit import limiter
from app.dependencies import AdminUser, CurrentPatient, DbSession
from app.models import User
from app.schemas.privacy import (
    ConsentOut,
    ConsentUpdate,
    IncidentIn,
    IncidentOut,
    IncidentUpdate,
    PrivacyRequestAdminOut,
    PrivacyRequestIn,
    PrivacyRequestOut,
    PrivacyRequestUpdate,
)
from app.services import consent_service, notification_service, privacy_service
from app.services.privacy_service import PrivacyError

router = APIRouter(tags=["privacy (Law 25)"])


def _fail(error: PrivacyError) -> HTTPException:
    return HTTPException(error.status_code, error.detail)


def _out(item) -> PrivacyRequestOut:
    return PrivacyRequestOut(
        id=item.id,
        type=item.type,
        details=item.details,
        status=item.status,
        requested_at=item.requested_at,
        due_at=item.due_at,
        completed_at=item.completed_at,
        outcome=item.outcome,
    )


def _admin_out(view: privacy_service.RequestView) -> PrivacyRequestAdminOut:
    return PrivacyRequestAdminOut(
        **_out(view.item).model_dump(),
        patient_id=view.patient.id,
        patient_name=f"{view.patient.first_name} {view.patient.last_name}",
        email=view.email,
        overdue=view.overdue,
    )


def _incident_out(incident) -> IncidentOut:
    return IncidentOut(
        id=incident.id,
        occurred_at=incident.occurred_at,
        discovered_at=incident.discovered_at,
        description=incident.description,
        data_categories=incident.data_categories,
        people_affected=incident.people_affected,
        risk_level=incident.risk_level,
        measures=incident.measures,
        cai_notified_at=incident.cai_notified_at,
        persons_notified_at=incident.persons_notified_at,
        recorded_by=incident.recorded_by,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        to_notify=privacy_service.to_notify(incident),
    )


# --- Patient ----------------------------------------------------------------------------------


@router.post("/me/privacy-requests", status_code=status.HTTP_201_CREATED)
@limiter.limit(rate_limit.BOOKING_LIMIT)
def submit_request(
    request: Request, body: PrivacyRequestIn, db: DbSession, patient: CurrentPatient
) -> PrivacyRequestOut:
    """Ask to see, correct or delete my information. The clinic answers within 30 days."""
    try:
        item = privacy_service.submit(db, patient, body.type, body.details, request)
    except PrivacyError as error:
        raise _fail(error) from None
    return _out(item)


@router.get("/me/privacy-requests")
def my_requests(db: DbSession, patient: CurrentPatient) -> list[PrivacyRequestOut]:
    return [_out(i) for i in privacy_service.my_requests(db, patient)]


# --- Administrator ------------------------------------------------------------------------------


def _consent_out(state: consent_service.ConsentState) -> ConsentOut:
    return ConsentOut(
        type=state.type,
        given=state.given,
        version=state.version,
        granted_at=state.granted_at,
        revoked_at=state.revoked_at,
        current_version=state.current_version,
        up_to_date=state.up_to_date,
    )


@router.get("/me/consents")
def my_consents(db: DbSession, patient: CurrentPatient) -> list[ConsentOut]:
    """What the patient agreed to, which version and when (Law 25: consent is visible)."""
    user = db.get(User, patient.user_id)
    return [_consent_out(s) for s in consent_service.my_consents(db, user)]


@router.put("/me/consents/electronic_comms")
def set_electronic_comms(
    request: Request, body: ConsentUpdate, db: DbSession, patient: CurrentPatient
) -> ConsentOut:
    """Give or withdraw the optional consent to non-essential messages, at any time."""
    user = db.get(User, patient.user_id)
    return _consent_out(
        consent_service.set_electronic_comms(db, user, patient, body.given, request)
    )


@router.post("/me/consents/privacy_policy")
def accept_privacy_policy(request: Request, db: DbSession, patient: CurrentPatient) -> ConsentOut:
    """Accept the current version of the privacy policy. It cannot be withdrawn here: closing
    the account (a deletion request) is how a patient stops all processing."""
    user = db.get(User, patient.user_id)
    return _consent_out(consent_service.accept_policy(db, user, patient, request))


@router.get("/admin/privacy-requests")
def list_requests(admin: AdminUser, db: DbSession) -> list[PrivacyRequestAdminOut]:
    """Open requests first, oldest deadline first; `overdue` when 30 days have passed."""
    return [_admin_out(v) for v in privacy_service.list_requests(db)]


@router.patch("/admin/privacy-requests/{request_id}")
def update_request(
    request_id: uuid.UUID,
    body: PrivacyRequestUpdate,
    request: Request,
    background: BackgroundTasks,
    admin: AdminUser,
    db: DbSession,
) -> PrivacyRequestOut:
    """In progress, completed or refused (with the answer). The patient is told by email."""
    try:
        item, email = privacy_service.update_request(
            db, admin, request_id, body.status, body.outcome, request
        )
    except PrivacyError as error:
        raise _fail(error) from None
    background.add_task(notification_service.send, email)
    return _out(item)


@router.get("/admin/privacy-requests/{request_id}/export")
def export_request(
    request_id: uuid.UUID, request: Request, admin: AdminUser, db: DbSession
) -> dict:
    """Personal information kept about the patient (access request). No clinical notes."""
    try:
        return privacy_service.export(db, admin, request_id, request)
    except PrivacyError as error:
        raise _fail(error) from None


@router.post("/admin/privacy-requests/{request_id}/erase")
def erase_request(
    request_id: uuid.UUID, request: Request, admin: AdminUser, db: DbSession
) -> PrivacyRequestOut:
    """Complete a deletion request: account closed, contact details erased, health record
    kept until the end of its retention period (reason written in the answer)."""
    try:
        item = privacy_service.erase(db, admin, request_id, request)
    except PrivacyError as error:
        raise _fail(error) from None
    return _out(item)


@router.get("/admin/incidents")
def list_incidents(admin: AdminUser, db: DbSession) -> list[IncidentOut]:
    return [_incident_out(i) for i in privacy_service.list_incidents(db)]


@router.post("/admin/incidents", status_code=status.HTTP_201_CREATED)
def record_incident(
    body: IncidentIn, request: Request, admin: AdminUser, db: DbSession
) -> IncidentOut:
    """Record a confidentiality incident. Entries are kept at least 5 years, never deleted."""
    try:
        incident = privacy_service.record_incident(db, admin, body.model_dump(), request)
    except PrivacyError as error:
        raise _fail(error) from None
    return _incident_out(incident)


@router.patch("/admin/incidents/{incident_id}")
def update_incident(
    incident_id: uuid.UUID, body: IncidentUpdate, request: Request, admin: AdminUser, db: DbSession
) -> IncidentOut:
    """Keep an entry up to date: measures taken, notification dates."""
    fields = body.model_dump(exclude_unset=True)
    required = ("description", "data_categories", "risk_level", "measures")
    if any(fields.get(name, "") is None for name in required):
        raise HTTPException(422, "Required fields cannot be emptied.")
    try:
        incident = privacy_service.update_incident(db, admin, incident_id, fields, request)
    except PrivacyError as error:
        raise _fail(error) from None
    return _incident_out(incident)
