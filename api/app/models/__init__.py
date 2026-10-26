"""All models are imported here so Alembic can find every table."""

from app.models.appointment import ACTIVE_STATUSES, APPOINTMENT_STATUSES, Appointment
from app.models.availability import AvailabilityException, AvailabilityRule
from app.models.patient import Patient
from app.models.service import Service, TherapistService
from app.models.therapist import Therapist
from app.models.user import ROLES, Consent, RefreshToken, User

__all__ = [
    "ACTIVE_STATUSES",
    "APPOINTMENT_STATUSES",
    "ROLES",
    "Appointment",
    "AvailabilityException",
    "AvailabilityRule",
    "Consent",
    "Patient",
    "RefreshToken",
    "Service",
    "Therapist",
    "TherapistService",
    "User",
]
