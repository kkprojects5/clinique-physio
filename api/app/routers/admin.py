"""Clinic administration (B-ADM-01, B-ADM-02, B-ADM-03). Administrators with MFA only."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status

from app.dependencies import AdminUser, DbSession
from app.schemas.admin import (
    AuditEntryOut,
    AuditPage,
    AuditQuery,
    ServiceAdminOut,
    ServiceCreate,
    ServiceUpdate,
    StaffActive,
    StaffCreate,
    StaffOut,
)
from app.schemas.billing import TherapistWeekOut, WeekReportOut
from app.services import admin_service, photo_service, report_service
from app.services.admin_service import AdminError, AuditFilter
from app.services.availability_service import today_local

router = APIRouter(prefix="/admin", tags=["administration"])


def _fail(error: AdminError) -> HTTPException:
    return HTTPException(error.status_code, error.detail)


def _service_out(service, therapist_ids) -> ServiceAdminOut:
    return ServiceAdminOut(
        id=service.id,
        name_fr=service.name_fr,
        name_en=service.name_en,
        description_fr=service.description_fr,
        description_en=service.description_en,
        duration_min=service.duration_min,
        price_cents=service.price_cents,
        deposit_cents=service.deposit_cents,
        is_initial_evaluation=service.is_initial_evaluation,
        is_active=service.is_active,
        therapist_ids=therapist_ids,
    )


def _staff_out(view: admin_service.StaffView) -> StaffOut:
    t = view.therapist
    return StaffOut(
        id=view.user.id,
        email=view.user.email,
        role=view.user.role,
        is_active=view.user.is_active,
        mfa_ready=view.user.mfa_enabled_at is not None,
        last_login_at=view.user.last_login_at,
        therapist_id=t.id if t else None,
        first_name=t.first_name if t else None,
        last_name=t.last_name if t else None,
        licence_number=t.licence_number if t else None,
        future_appointments=view.future_appointments,
        photo_url=photo_service.photo_url(t) if t else None,
    )


# --- Services (B-ADM-01) ---------------------------------------------------------------------


@router.get("/services")
def list_services(admin: AdminUser, db: DbSession) -> list[ServiceAdminOut]:
    """All services, inactive ones included, with the therapists who give them."""
    return [_service_out(s, ids) for s, ids in admin_service.list_services(db)]


@router.post("/services", status_code=status.HTTP_201_CREATED)
def create_service(
    body: ServiceCreate, request: Request, admin: AdminUser, db: DbSession
) -> ServiceAdminOut:
    fields = body.model_dump(exclude={"therapist_ids"})
    try:
        service, ids = admin_service.create_service(db, admin, fields, body.therapist_ids, request)
    except AdminError as error:
        raise _fail(error) from None
    return _service_out(service, ids)


@router.patch("/services/{service_id}")
def update_service(
    service_id: uuid.UUID, body: ServiceUpdate, request: Request, admin: AdminUser, db: DbSession
) -> ServiceAdminOut:
    """Change a service. `is_active: false` stops new bookings; booked ones stay."""
    fields = body.model_dump(exclude_unset=True, exclude={"therapist_ids"})
    if any(value is None for key, value in fields.items() if not key.startswith("description")):
        raise HTTPException(422, "Only descriptions can be emptied.")
    therapist_ids = body.therapist_ids if "therapist_ids" in body.model_fields_set else None
    try:
        service, ids = admin_service.update_service(
            db, admin, service_id, fields, therapist_ids, request
        )
    except AdminError as error:
        raise _fail(error) from None
    return _service_out(service, ids)


# --- Staff (B-ADM-01) ------------------------------------------------------------------------


@router.get("/staff")
def list_staff(admin: AdminUser, db: DbSession) -> list[StaffOut]:
    return [_staff_out(v) for v in admin_service.list_staff(db)]


@router.post("/staff", status_code=status.HTTP_201_CREATED)
def create_staff(
    body: StaffCreate,
    request: Request,
    background: BackgroundTasks,
    admin: AdminUser,
    db: DbSession,
) -> StaffOut:
    """Create a therapist or front-desk account. They receive a link to choose their password."""
    therapist = body.therapist.model_dump() if body.therapist else None
    try:
        view, invitation = admin_service.create_staff(
            db, admin, body.email, body.role, body.language, therapist, request
        )
    except AdminError as error:
        raise _fail(error) from None
    background.add_task(admin_service.send, invitation)
    return _staff_out(view)


@router.patch("/staff/{user_id}")
def set_staff_active(
    user_id: uuid.UUID, body: StaffActive, request: Request, admin: AdminUser, db: DbSession
) -> StaffOut:
    """Activate or deactivate a staff account; deactivating closes its sessions at once."""
    try:
        view = admin_service.set_active(db, admin, user_id, body.is_active, request)
    except AdminError as error:
        raise _fail(error) from None
    return _staff_out(view)


@router.post("/staff/{user_id}/invitation", status_code=status.HTTP_204_NO_CONTENT)
def resend_invitation(
    user_id: uuid.UUID,
    request: Request,
    background: BackgroundTasks,
    admin: AdminUser,
    db: DbSession,
) -> None:
    """Send a new password link (the previous one stops working)."""
    try:
        invitation = admin_service.resend_invitation(db, admin, user_id, request)
    except AdminError as error:
        raise _fail(error) from None
    background.add_task(admin_service.send, invitation)


# --- Audit log (B-ADM-03) --------------------------------------------------------------------


@router.get("/audit")
def read_audit(
    query: Annotated[AuditQuery, Query()], request: Request, admin: AdminUser, db: DbSession
) -> AuditPage:
    """Who did what, newest first, 50 per page. Days are in Montréal time. This read is logged."""
    rows, next_id = admin_service.read_audit(db, admin, AuditFilter(**query.model_dump()), request)
    return AuditPage(
        entries=[
            AuditEntryOut(
                id=r.entry.id,
                created_at=r.entry.created_at,
                actor_email=r.actor_email,
                actor_role=r.actor_role,
                action=r.entry.action,
                resource_type=r.entry.resource_type,
                resource_id=r.entry.resource_id,
                patient_id=r.entry.patient_id,
                patient_name=r.patient_name,
                ip=str(r.entry.ip) if r.entry.ip else None,
                client_app=r.entry.client_app,
                unusual=r.unusual,
            )
            for r in rows
        ],
        next_before_id=next_id,
    )


# --- Weekly report (B-ADM-02) ----------------------------------------------------------------


@router.get("/reports/weekly")
def weekly_report(
    admin: AdminUser, db: DbSession, week: Annotated[date | None, Query()] = None
) -> WeekReportOut:
    """The week (Monday to Sunday, Montréal time) that contains `week`; this week by default.

    Counts and totals only: no patient is named."""
    report = report_service.weekly(db, week or today_local())
    return WeekReportOut(
        week_start=report.week_start,
        week_end=report.week_end,
        appointments=report.appointments,
        seen=report.seen,
        no_shows=report.no_shows,
        cancelled_by_patient=report.statuses["cancelled_by_patient"],
        cancelled_by_clinic=report.statuses["cancelled_by_clinic"],
        confirmed=report.statuses["confirmed"],
        no_show_rate=report.no_show_rate,
        occupancy=report.occupancy,
        revenue_cents=report.revenue_cents,
        deposits_cents=report.deposits_cents,
        desk_cents=report.desk_cents,
        refunds_cents=report.refunds_cents,
        therapists=[
            TherapistWeekOut(
                therapist_id=t.therapist.id,
                first_name=t.therapist.first_name,
                last_name=t.therapist.last_name,
                appointments=t.appointments,
                seen=t.seen,
                no_shows=t.no_shows,
                booked_minutes=t.booked_minutes,
                working_minutes=t.working_minutes,
                occupancy=t.occupancy,
            )
            for t in report.therapists
        ],
    )


# --- Therapist photos (B-AVL-05) -------------------------------------------------------------


@router.put("/therapists/{therapist_id}/photo")
async def upload_photo(
    therapist_id: uuid.UUID, request: Request, admin: AdminUser, db: DbSession
) -> dict[str, str | None]:
    """The image is the request body (Content-Type image/jpeg, image/png or image/webp).

    It is re-encoded as a 400 x 400 JPEG without metadata before it is stored."""
    kind = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if kind not in photo_service.CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Use a JPEG, PNG or WebP image.")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > photo_service.MAX_BYTES:
        raise HTTPException(status_code=413, detail="The photo must be 3 MB or less.")
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > photo_service.MAX_BYTES:
            raise HTTPException(status_code=413, detail="The photo must be 3 MB or less.")
    try:
        therapist = photo_service.set_photo(db, admin, therapist_id, bytes(data), request)
    except photo_service.NotFound:
        raise HTTPException(status_code=404, detail="Therapist not found.") from None
    except photo_service.PhotoError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return {"photo_url": photo_service.photo_url(therapist)}


@router.delete("/therapists/{therapist_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(therapist_id: uuid.UUID, request: Request, admin: AdminUser, db: DbSession):
    try:
        photo_service.remove_photo(db, admin, therapist_id, request)
    except photo_service.NotFound:
        raise HTTPException(status_code=404, detail="Therapist not found.") from None
