"""Booking emails to the patient (B-BKG-01): confirmed, moved, cancelled.

- Sent after the change is saved, in the background, so the answer is not slowed down.
- They contain only practical information: date and time in Montréal time, service,
  physiotherapist, address and the cancellation rule. Never clinical information (BR-8).
- These are transactional messages about a booking the patient made, so they are sent even
  without consent to marketing emails.
- Without an email provider (R-9), the email is written to the log with a masked address.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Appointment, Patient, Payment, Service, Therapist, User
from app.services.email import send_email
from app.services.password_reset_service import Email
from app.services.slots import CLINIC_TZ

ADDRESS = {"fr": "4200, rue Saint-Denis, Montréal", "en": "4200 Saint-Denis Street, Montréal"}
SUBJECTS = {
    "confirmed": {"fr": "Rendez-vous confirmé", "en": "Appointment confirmed"},
    "moved": {"fr": "Rendez-vous déplacé", "en": "Appointment moved"},
    "cancelled": {"fr": "Rendez-vous annulé", "en": "Appointment cancelled"},
}
INTRO = {
    "confirmed": {
        "fr": "Votre rendez-vous est confirmé.",
        "en": "Your appointment is confirmed.",
    },
    "moved": {
        "fr": "Votre rendez-vous a été déplacé. Voici le nouveau moment.",
        "en": "Your appointment was moved. Here is the new time.",
    },
    "cancelled": {"fr": "Votre rendez-vous est annulé.", "en": "Your appointment is cancelled."},
}
REFUND = {
    "refunded": {
        "fr": "L'acompte payé en ligne sera remboursé sur votre carte.",
        "en": "The deposit paid online will be refunded to your card.",
    },
    "kept": {
        "fr": "L'acompte payé en ligne est conservé (annulation moins de 24 heures avant).",
        "en": "The deposit paid online is kept (cancelled less than 24 hours before).",
    },
    "nothing": {
        "fr": "Rien n'avait été payé en ligne : il n'y a rien à rembourser.",
        "en": "Nothing was paid online, so there is nothing to refund.",
    },
}
RULE = {
    "fr": "Pour annuler ou déplacer sans frais, faites-le plus de 24 heures avant dans « Mes "
    "rendez-vous » : {link}. Moins de 24 heures avant, appelez l'accueil au 514-555-0100.",
    "en": 'To cancel or move at no cost, do it more than 24 hours before in "My '
    'appointments": {link}. Less than 24 hours before, call the front desk at 514-555-0100.',
}
LABELS = {
    "fr": {"when": "Quand", "service": "Service", "therapist": "Physiothérapeute",
           "address": "Adresse"},
    "en": {"when": "When", "service": "Service", "therapist": "Physiotherapist",
           "address": "Address"},
}  # fmt: skip
WHEN_FORMAT = {"fr": "{day} à {time}", "en": "{day} at {time}"}
DAYS = {
    "fr": ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
}
MONTHS = {
    "fr": [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ],
    "en": [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ],
}  # fmt: skip


def when(start: datetime, language: str) -> str:
    """'mardi 24 novembre 2026 à 10 h 00' / 'Tuesday, November 24, 2026 at 10:00 a.m.'"""
    local = start.astimezone(CLINIC_TZ)
    weekday, month = DAYS[language][local.weekday()], MONTHS[language][local.month - 1]
    if language == "fr":
        day = f"{weekday} {local.day} {month} {local.year}"
        time = f"{local.hour} h {local:%M}"
    else:
        day = f"{weekday}, {month} {local.day}, {local.year}"
        hour = local.hour % 12 or 12
        time = f"{hour}:{local:%M} {'a.m.' if local.hour < 12 else 'p.m.'}"
    return WHEN_FORMAT[language].format(day=day, time=time)


def _refund_case(db: Session, appointment: Appointment, refund_due: bool | None) -> str:
    """What happened to the money: a deposit paid online is refunded only if due (24 h rule)."""
    paid = db.scalar(
        select(Payment.id).where(
            Payment.appointment_id == appointment.id,
            Payment.type == "deposit",
            Payment.status == "succeeded",
        )
    )
    if paid is None:
        return "nothing"
    return "refunded" if refund_due else "kept"


def booking_email(
    db: Session, appointment: Appointment, kind: str, refunded: bool | None = None
) -> Email | None:
    """The email for this change, or None if the patient has no active account."""
    patient = db.get(Patient, appointment.patient_id)
    user = db.get(User, patient.user_id) if patient else None
    if user is None or not user.is_active:
        return None
    lang = user.language
    service = db.get(Service, appointment.service_id)
    therapist = db.get(Therapist, appointment.therapist_id)
    label = LABELS[lang]
    sep = " : " if lang == "fr" else ": "  # French typography puts a space before the colon
    service_name = service.name_fr if lang == "fr" else service.name_en
    lines = [
        INTRO[kind][lang],
        "",
        f"{label['when']}{sep}{when(appointment.during.lower, lang)}",
        f"{label['service']}{sep}{service_name}",
        f"{label['therapist']}{sep}{therapist.first_name} {therapist.last_name}",
        f"{label['address']}{sep}{ADDRESS[lang]}",
        "",
    ]
    if kind == "cancelled":
        lines.append(REFUND[_refund_case(db, appointment, refunded)][lang])
    else:
        lines.append(RULE[lang].format(link=f"{settings.web_base_url}/mes-rendez-vous"))
    subject = f"{SUBJECTS[kind][lang]} — Clinique Physio Mont-Royal"
    return Email(user.email, subject, "\n".join(lines))


def confirmed_by_payment(db: Session, payment_intent_id: str) -> Email | None:
    """The confirmation email after Stripe's webhook confirmed the deposit."""
    payment = db.scalar(select(Payment).where(Payment.stripe_id == payment_intent_id))
    appointment = db.get(Appointment, payment.appointment_id) if payment else None
    return booking_email(db, appointment, "confirmed") if appointment else None


def send(email: Email | None) -> None:
    if email is not None:
        send_email(email.to, email.subject, email.body)
