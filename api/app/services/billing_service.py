"""What an appointment costs and what was paid; desk payments and receipts (B-FRD-05, B-BKG-10).

- The price is the service price. The deposit is paid online with Stripe (B-BKG-04); the rest
  (the balance) is paid at the clinic, by cash, debit or credit card on the clinic's terminal.
- The desk records the balance once the patient has arrived. The amount is always computed
  by the server (price minus what was already paid): the desk cannot type another amount.
- A receipt (PDF) lists the clinic, the physiotherapist and licence number, the service, the
  date and every amount paid, for the patient's insurer. It is available once the patient
  has come and something was paid. It never contains clinical information.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Request
from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Appointment, Patient, Payment, Service, Therapist, User
from app.models.payment import DESK_METHODS
from app.services import audit_service
from app.services.booking_service import BookingError, NotFound, locked_appointment
from app.services.slots import CLINIC_TZ

# The patient came: the balance can be paid and a receipt given.
CAME = ("checked_in", "completed")

CLINIC = {
    "name": "Clinique Physio Mont-Royal",
    "address": "4200, rue Saint-Denis, Montréal (Québec)",
    "phone": "514-555-0100",
}
METHOD_NAMES = {
    "fr": {"stripe": "en ligne (carte)", "cash": "comptant", "debit": "débit", "credit": "crédit"},
    "en": {"stripe": "online (card)", "cash": "cash", "debit": "debit", "credit": "credit"},
}
TEXT = {
    "fr": {
        "title": "Reçu",
        "number": "Reçu no",
        "issued": "Émis le",
        "patient": "Patient",
        "therapist": "Physiothérapeute",
        "licence": "Permis no",
        "service": "Service",
        "date": "Date du rendez-vous",
        "price": "Prix du service",
        "deposit": "Dépôt payé",
        "balance": "Solde payé",
        "refund": "Remboursement",
        "total": "Total payé",
        "due": "Reste à payer",
        "demo": "Clinique fictive : document produit pour un projet étudiant.",
    },
    "en": {
        "title": "Receipt",
        "number": "Receipt no.",
        "issued": "Issued on",
        "patient": "Patient",
        "therapist": "Physiotherapist",
        "licence": "Licence no.",
        "service": "Service",
        "date": "Appointment date",
        "price": "Service price",
        "deposit": "Deposit paid",
        "balance": "Balance paid",
        "refund": "Refund",
        "total": "Total paid",
        "due": "Left to pay",
        "demo": "Fictional clinic: document produced for a student project.",
    },
}


@dataclass
class Billing:
    appointment: Appointment
    price_cents: int
    deposit_paid_cents: int
    balance_paid_cents: int
    refunded_cents: int
    payments: list[Payment]

    @property
    def paid_cents(self) -> int:
        return self.deposit_paid_cents + self.balance_paid_cents - self.refunded_cents

    @property
    def due_cents(self) -> int:
        """Left to pay. Nothing is due for an appointment that did not take place."""
        if self.appointment.status not in (*CAME, "confirmed"):
            return 0
        return max(self.price_cents - self.paid_cents, 0)

    @property
    def can_pay(self) -> bool:
        return self.appointment.status in CAME and self.due_cents > 0

    @property
    def receipt_available(self) -> bool:
        return self.appointment.status in CAME and self.paid_cents > 0


def _summary(db: Session, appointment: Appointment) -> Billing:
    service = db.get(Service, appointment.service_id)
    payments = list(
        db.scalars(
            select(Payment)
            .where(Payment.appointment_id == appointment.id, Payment.status == "succeeded")
            .order_by(Payment.created_at)
        )
    )

    def total(kind: str) -> int:
        return sum(p.amount_cents for p in payments if p.type == kind)

    return Billing(
        appointment=appointment,
        price_cents=service.price_cents,
        deposit_paid_cents=total("deposit"),
        balance_paid_cents=total("balance"),
        refunded_cents=total("refund"),
        payments=payments,
    )


def summary(db: Session, appointment_id: uuid.UUID) -> Billing:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise NotFound
    return _summary(db, appointment)


def record_balance(
    db: Session, actor: User, appointment_id: uuid.UUID, method: str, request: Request | None
) -> Billing:
    """The patient pays the rest at the desk. The amount is computed here, never typed."""
    if method not in DESK_METHODS:
        raise BookingError("Choose cash, debit or credit.")
    appointment = locked_appointment(db, appointment_id)  # one desk at a time
    billing = _summary(db, appointment)
    if appointment.status not in CAME:
        db.rollback()
        raise BookingError("The balance is paid once the patient has arrived.")
    if billing.due_cents == 0:
        db.rollback()
        raise BookingError("Nothing is left to pay for this appointment.")
    db.add(
        Payment(
            appointment_id=appointment.id,
            amount_cents=billing.due_cents,
            type="balance",
            method=method,
            status="succeeded",
            recorded_by=actor.id,
        )
    )
    audit_service.log(
        db, actor.id, "payment", "appointment", appointment.id, appointment.patient_id, request
    )
    db.commit()
    return _summary(db, appointment)


RECEIPTS_LIMIT = 50


def my_receipts(db: Session, patient: Patient) -> list[tuple[Appointment, Billing]]:
    """The patient's own past visits that have a receipt, newest first."""
    visits = db.scalars(
        select(Appointment)
        .where(Appointment.patient_id == patient.id, Appointment.status.in_(CAME))
        .order_by(Appointment.during.desc())
        .limit(RECEIPTS_LIMIT)
    ).all()
    found = [(a, _summary(db, a)) for a in visits]
    return [(a, b) for a, b in found if b.receipt_available]


def own_appointment(db: Session, patient: Patient, appointment_id: uuid.UUID) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None or appointment.patient_id != patient.id:
        raise NotFound  # another patient's appointment looks the same as a missing one
    return appointment


def _money(cents: int, lang: str) -> str:
    whole, part = divmod(abs(cents), 100)
    sign = "-" if cents < 0 else ""
    if lang == "fr":
        return f"{sign}{whole:,}".replace(",", " ") + f",{part:02d} $"
    return f"{sign}${whole:,}.{part:02d}"


def _day(moment: datetime, lang: str) -> str:
    local = moment.astimezone(CLINIC_TZ)
    if lang == "fr":
        return local.strftime("%Y-%m-%d, %H h %M")
    return local.strftime("%Y-%m-%d, %I:%M %p").replace(" 0", " ")


def receipt_number(appointment: Appointment) -> str:
    return "R-" + appointment.id.hex[:8].upper()


def receipt_pdf(
    db: Session,
    actor: User,
    appointment: Appointment,
    lang: str,
    request: Request | None,
    now: datetime | None = None,
) -> bytes:
    """The receipt for the patient's insurer. 409 until the patient came and paid something."""
    billing = _summary(db, appointment)
    if not billing.receipt_available:
        raise BookingError("A receipt is available once the patient has come and paid.")
    lang = lang if lang in TEXT else "fr"
    words = TEXT[lang]
    service = db.get(Service, appointment.service_id)
    therapist = db.get(Therapist, appointment.therapist_id)
    patient = db.get(Patient, appointment.patient_id)
    service_name = service.name_fr if lang == "fr" else service.name_en

    pdf = FPDF(format="Letter")
    pdf.set_title(f"{words['title']} {receipt_number(appointment)}")
    pdf.set_author(CLINIC["name"])
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, CLINIC["name"], new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, CLINIC["address"], new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, CLINIC["phone"], new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 9, words["title"], new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)

    def line(label: str, value: str, bold: bool = False) -> None:
        pdf.set_font("Helvetica", "B" if bold else "", 11)
        pdf.cell(70, 7, label)
        pdf.cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")

    line(words["number"], receipt_number(appointment))
    line(words["issued"], _day(now or datetime.now(UTC), lang))
    pdf.ln(3)
    line(words["patient"], f"{patient.first_name} {patient.last_name}")
    line(words["therapist"], f"{therapist.first_name} {therapist.last_name}")
    line(words["licence"], therapist.licence_number)
    line(words["service"], service_name)  # the name already says how long
    line(words["date"], _day(appointment.during.lower, lang))
    pdf.ln(3)
    line(words["price"], _money(billing.price_cents, lang))
    methods = METHOD_NAMES[lang]
    for payment in billing.payments:
        label = words[payment.type] + f" ({methods[payment.method]})"
        amount = -payment.amount_cents if payment.type == "refund" else payment.amount_cents
        line(label, _money(amount, lang))
    line(words["total"], _money(billing.paid_cents, lang), bold=True)
    if billing.due_cents:
        line(words["due"], _money(billing.due_cents, lang))
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 5, words["demo"], new_x="LMARGIN", new_y="NEXT")

    audit_service.log(
        db, actor.id, "receipt", "appointment", appointment.id, appointment.patient_id, request
    )
    db.commit()
    return bytes(pdf.output())
