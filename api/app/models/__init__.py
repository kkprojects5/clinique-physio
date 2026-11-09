"""All models are imported here so Alembic can find every table."""

from app.models.appointment import (
    ACTIVE_STATUSES,
    APPOINTMENT_STATUSES,
    UNPAID_STATUSES,
    Appointment,
    AppointmentStatusHistory,
)
from app.models.availability import AvailabilityException, AvailabilityRule
from app.models.clinical import AuditLog, ClinicalNote
from app.models.exercise import Exercise, ExerciseLog, Program, ProgramItem
from app.models.patient import Patient
from app.models.payment import Payment, PaymentEvent
from app.models.service import Service, TherapistService
from app.models.therapist import Therapist
from app.models.user import ROLES, Consent, PasswordResetToken, RefreshToken, User

__all__ = [
    "ACTIVE_STATUSES",
    "APPOINTMENT_STATUSES",
    "ROLES",
    "UNPAID_STATUSES",
    "Appointment",
    "AuditLog",
    "ClinicalNote",
    "Exercise",
    "ExerciseLog",
    "AppointmentStatusHistory",
    "AvailabilityException",
    "AvailabilityRule",
    "Consent",
    "PasswordResetToken",
    "Patient",
    "Payment",
    "PaymentEvent",
    "Program",
    "ProgramItem",
    "RefreshToken",
    "Service",
    "Therapist",
    "TherapistService",
    "User",
]
