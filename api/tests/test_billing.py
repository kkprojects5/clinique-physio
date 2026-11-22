"""Balance paid at the desk (B-FRD-05) and the receipt for insurers (B-BKG-10)."""

import uuid

import pytest
from sqlalchemy import select

from app.models import AuditLog, Payment, User
from tests.test_booking import at, clinic, place  # noqa: F401  (fixture)
from tests.test_clinical import as_staff
from tests.test_login import make_user
from tests.test_schedules import make_patient, patient_headers

DESK = "/api/v1/desk/appointments"
MINE = "/api/v1/appointments"


@pytest.fixture
def desk(db):
    return make_user(db, f"accueil-{uuid.uuid4().hex[:6]}@example.com", role="front_desk")


def headers(desk):
    return as_staff(desk, role="front_desk", app="desktop")


def paid_deposit(db, appointment, cents=2000):
    db.add(
        Payment(
            appointment_id=appointment.id,
            amount_cents=cents,
            type="deposit",
            method="stripe",
            status="succeeded",
            stripe_id=f"pi_{uuid.uuid4().hex[:10]}",
        )
    )
    db.commit()


def visit(db, clinic, status="checked_in", deposit=True):  # noqa: F811
    marie = make_patient(db, "Marie")
    appointment = place(db, marie, clinic["anne"], clinic["treatment"], at(10), status=status)
    if deposit:
        paid_deposit(db, appointment)
    return marie, appointment


# --- What is left to pay ------------------------------------------------------------------------


def test_billing_shows_price_paid_and_balance(client, db, clinic, desk):  # noqa: F811
    _, appointment = visit(db, clinic)

    body = client.get(f"{DESK}/{appointment.id}/billing", headers=headers(desk)).json()

    assert body["price_cents"] == 8000
    assert body["paid_cents"] == 2000
    assert body["due_cents"] == 6000
    assert body["can_pay"] is True
    assert body["receipt_number"] == "R-" + appointment.id.hex[:8].upper()
    assert [(p["type"], p["method"]) for p in body["payments"]] == [("deposit", "stripe")]


def test_nothing_is_due_for_a_cancelled_appointment(client, db, clinic, desk):  # noqa: F811
    _, appointment = visit(db, clinic, status="cancelled_by_patient", deposit=False)

    body = client.get(f"{DESK}/{appointment.id}/billing", headers=headers(desk)).json()

    assert body["due_cents"] == 0 and body["can_pay"] is False


# --- Paying at the desk -------------------------------------------------------------------------


def test_desk_records_the_balance_computed_by_the_server(client, db, clinic, desk):  # noqa: F811
    _, appointment = visit(db, clinic)

    response = client.post(
        f"{DESK}/{appointment.id}/payments", json={"method": "debit"}, headers=headers(desk)
    )

    assert response.status_code == 201
    body = response.json()
    assert body["paid_cents"] == 8000 and body["due_cents"] == 0 and body["can_pay"] is False
    balance = db.scalar(select(Payment).where(Payment.type == "balance"))
    assert (balance.amount_cents, balance.method, balance.recorded_by) == (6000, "debit", desk.id)
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "payment"))
    assert entry.patient_id == appointment.patient_id


def test_an_amount_sent_by_the_client_is_ignored(client, db, clinic, desk):  # noqa: F811
    _, appointment = visit(db, clinic)

    client.post(
        f"{DESK}/{appointment.id}/payments",
        json={"method": "cash", "amount_cents": 1},
        headers=headers(desk),
    )

    assert db.scalar(select(Payment.amount_cents).where(Payment.type == "balance")) == 6000


def test_the_balance_is_paid_once(client, db, clinic, desk):  # noqa: F811
    _, appointment = visit(db, clinic)
    url = f"{DESK}/{appointment.id}/payments"
    client.post(url, json={"method": "cash"}, headers=headers(desk))

    again = client.post(url, json={"method": "cash"}, headers=headers(desk))

    assert again.status_code == 409


def test_payment_only_after_the_patient_arrived(client, db, clinic, desk):  # noqa: F811
    _, appointment = visit(db, clinic, status="confirmed")

    response = client.post(
        f"{DESK}/{appointment.id}/payments", json={"method": "cash"}, headers=headers(desk)
    )

    assert response.status_code == 409


@pytest.mark.parametrize("method", ["stripe", "cheque", ""])
def test_only_desk_methods_are_accepted(client, db, clinic, desk, method):  # noqa: F811
    _, appointment = visit(db, clinic)

    response = client.post(
        f"{DESK}/{appointment.id}/payments", json={"method": method}, headers=headers(desk)
    )

    assert response.status_code == 422


def test_patients_and_therapists_cannot_record_payments(client, db, clinic):  # noqa: F811
    marie, appointment = visit(db, clinic)
    therapist = db.get(User, clinic["anne"].user_id)
    url = f"{DESK}/{appointment.id}/payments"

    as_patient = client.post(url, json={"method": "cash"}, headers=patient_headers(marie))
    as_therapist = client.post(
        url, json={"method": "cash"}, headers=as_staff(therapist, role="therapist")
    )

    assert as_patient.status_code == 403 and as_therapist.status_code == 403


# --- Receipt ------------------------------------------------------------------------------------


def test_patient_downloads_a_pdf_receipt(client, db, clinic, desk):  # noqa: F811
    marie, appointment = visit(db, clinic, status="completed")

    response = client.get(f"{MINE}/{appointment.id}/receipt", headers=patient_headers(marie))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "no-store"
    assert "R-" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "receipt"))
    assert entry.actor_id == marie.user_id


def test_receipt_text_has_the_insurer_details(db, clinic, desk):  # noqa: F811
    from app.services import billing_service

    marie, appointment = visit(db, clinic, status="completed")
    billing_service.record_balance(db, desk, appointment.id, "credit", None)
    therapist = clinic["anne"]

    pdf = billing_service.receipt_pdf(db, desk, appointment, "fr", None)

    import zlib

    text = b"".join(
        zlib.decompress(chunk.split(b"stream\n", 1)[1].rsplit(b"\nendstream", 1)[0])
        for chunk in pdf.split(b"endobj")
        if b"/FlateDecode" in chunk and b"stream\n" in chunk
    ).decode("latin-1")
    for expected in (
        "Clinique Physio Mont-Royal",
        therapist.licence_number,
        "Traitement",
        "Marie",
        "80,00 $",
        "Clinique fictive",
    ):
        assert expected in text


def test_no_receipt_before_the_visit(client, db, clinic):  # noqa: F811
    marie, appointment = visit(db, clinic, status="confirmed")

    response = client.get(f"{MINE}/{appointment.id}/receipt", headers=patient_headers(marie))

    assert response.status_code == 409


def test_no_receipt_for_another_patients_appointment(client, db, clinic):  # noqa: F811
    _, appointment = visit(db, clinic, status="completed")
    paul = make_patient(db, "Paul")

    response = client.get(f"{MINE}/{appointment.id}/receipt", headers=patient_headers(paul))

    assert response.status_code == 404


def test_desk_prints_the_receipt_in_english(client, db, clinic, desk):  # noqa: F811
    _, appointment = visit(db, clinic)

    response = client.get(
        f"{DESK}/{appointment.id}/receipt", params={"lang": "en"}, headers=headers(desk)
    )

    assert response.status_code == 200 and response.content.startswith(b"%PDF")


def test_patient_lists_only_own_visits_with_a_receipt(client, db, clinic):  # noqa: F811
    marie, appointment = visit(db, clinic, status="completed")
    place(db, marie, clinic["sophie"], clinic["treatment"], at(9), status="completed")  # unpaid
    other, _ = visit(db, clinic, status="completed")

    listed = client.get("/api/v1/me/receipts", headers=patient_headers(marie)).json()

    assert [r["appointment_id"] for r in listed] == [str(appointment.id)]
    assert listed[0]["paid_cents"] == 2000 and listed[0]["therapist"].endswith("Lefebvre")
