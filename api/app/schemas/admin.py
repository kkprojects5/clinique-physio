import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Duration = Literal[30, 45, 60]
MAX_CENTS = 100_000  # $1,000: no service costs more


class ServiceAdminOut(BaseModel):
    id: uuid.UUID
    name_fr: str
    name_en: str
    description_fr: str | None
    description_en: str | None
    duration_min: int
    price_cents: int
    deposit_cents: int
    is_initial_evaluation: bool
    is_active: bool
    therapist_ids: list[uuid.UUID]


class ServiceCreate(BaseModel):
    name_fr: str = Field(min_length=2, max_length=120)
    name_en: str = Field(min_length=2, max_length=120)
    description_fr: str | None = Field(default=None, max_length=1000)
    description_en: str | None = Field(default=None, max_length=1000)
    duration_min: Duration
    price_cents: int = Field(ge=0, le=MAX_CENTS)
    deposit_cents: int = Field(ge=0, le=MAX_CENTS)
    is_initial_evaluation: bool = False
    therapist_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)


class ServiceUpdate(BaseModel):
    """Only the fields sent are changed."""

    name_fr: str | None = Field(default=None, min_length=2, max_length=120)
    name_en: str | None = Field(default=None, min_length=2, max_length=120)
    description_fr: str | None = Field(default=None, max_length=1000)
    description_en: str | None = Field(default=None, max_length=1000)
    duration_min: Duration | None = None
    price_cents: int | None = Field(default=None, ge=0, le=MAX_CENTS)
    deposit_cents: int | None = Field(default=None, ge=0, le=MAX_CENTS)
    is_initial_evaluation: bool | None = None
    is_active: bool | None = None
    therapist_ids: list[uuid.UUID] | None = Field(default=None, max_length=50)


class StaffOut(BaseModel):
    id: uuid.UUID  # the user account
    email: str
    role: str
    is_active: bool
    mfa_ready: bool  # has set up the 6-digit code
    last_login_at: datetime | None
    therapist_id: uuid.UUID | None
    first_name: str | None
    last_name: str | None
    licence_number: str | None
    future_appointments: int  # a deactivated therapist's appointments must be moved
    photo_url: str | None = None  # therapists only


class TherapistFields(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    licence_number: str = Field(min_length=3, max_length=30)
    languages: list[Literal["fr", "en", "ar", "vi", "ru", "es"]] = Field(
        default_factory=lambda: ["fr", "en"], max_length=6
    )


class StaffCreate(BaseModel):
    email: EmailStr
    role: Literal["therapist", "front_desk"]
    language: Literal["fr", "en"] = "fr"
    therapist: TherapistFields | None = None


class StaffActive(BaseModel):
    is_active: bool


class AuditEntryOut(BaseModel):
    id: int
    created_at: datetime
    actor_email: str | None
    actor_role: str | None
    action: str
    resource_type: str
    resource_id: uuid.UUID | None
    patient_id: uuid.UUID | None
    patient_name: str | None
    ip: str | None
    client_app: str | None
    unusual: bool  # refused access, or many different patients read in one hour


class AuditPage(BaseModel):
    entries: list[AuditEntryOut]
    next_before_id: int | None


class AuditQuery(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    action: str | None = Field(default=None, max_length=30)
    resource_type: str | None = Field(default=None, max_length=30)
    actor_email: str | None = Field(default=None, max_length=254)
    patient_id: uuid.UUID | None = None
    before_id: int | None = Field(default=None, ge=1)
    limit: int = Field(default=50, ge=1, le=100)
