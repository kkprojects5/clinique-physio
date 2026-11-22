"""Weekly report for the administrator (B-ADM-02): counts and totals, no names."""

from datetime import timedelta

from sqlalchemy.dialects.postgresql import Range

from app.models import AvailabilityException, Payment
from app.services.report_service import monday_of, weekly
from tests.test_availability import next_monday
from tests.test_booking import at, clinic, place  # noqa: F401  (fixture)
from tests.test_clinical import as_staff
from tests.test_login import make_user
from tests.test_privacy import admin, headers  # noqa: F401  (fixtures)
from tests.test_schedules import make_patient

REPORT = "/api/v1/admin/reports/weekly"


def busy_week(db, clinic):  # noqa: F811
    """Monday: Anne sees 2 patients, 1 no-show, 1 cancellation; Sophie has 1 coming."""
    patients = [make_patient(db, name) for name in ("Marie", "Paul", "Luc", "Zoé", "Lina")]
    anne, sophie, treatment = clinic["anne"], clinic["sophie"], clinic["treatment"]
    seen = place(db, patients[0], anne, treatment, at(8), status="completed")
    place(db, patients[1], anne, treatment, at(9), status="checked_in")
    place(db, patients[2], anne, treatment, at(10), status="no_show")
    place(db, patients[3], anne, treatment, at(11), status="cancelled_by_patient")
    place(db, patients[4], sophie, treatment, at(8), status="confirmed")
    place(db, patients[4], sophie, treatment, at(9), status="expired")  # an unpaid hold
    for kind, cents in (("deposit", 2000), ("balance", 6000), ("refund", 2000)):
        db.add(
            Payment(
                appointment_id=seen.id,
                amount_cents=cents,
                type=kind,
                method="stripe" if kind != "balance" else "cash",
                status="succeeded",
            )
        )
    db.commit()


def test_counts_of_the_week(db, clinic):  # noqa: F811
    busy_week(db, clinic)

    report = weekly(db, next_monday())

    assert report.week_start == next_monday()
    assert report.appointments == 5  # the expired hold is not an appointment
    assert report.seen == 2
    assert report.no_shows == 1
    assert report.statuses["cancelled_by_patient"] == 1
    assert report.no_show_rate == round(1 / 3, 3)


def test_occupancy_uses_working_hours_and_booked_time(db, clinic):  # noqa: F811
    busy_week(db, clinic)

    report = weekly(db, next_monday())

    anne = next(t for t in report.therapists if t.therapist.id == clinic["anne"].id)
    assert anne.working_minutes == 240  # Monday 8:00 to 12:00
    assert anne.booked_minutes == 90  # seen x2 + no-show; the cancellation frees its time
    assert report.occupancy == round((90 + 30) / 480, 3)


def test_time_off_reduces_working_hours(db, clinic):  # noqa: F811
    db.add(
        AvailabilityException(
            therapist_id=clinic["anne"].id, during=Range(at(8), at(10)), reason="formation"
        )
    )
    db.commit()

    report = weekly(db, next_monday())

    anne = next(t for t in report.therapists if t.therapist.id == clinic["anne"].id)
    assert anne.working_minutes == 120


def test_revenue_is_money_received_minus_refunds(db, clinic):  # noqa: F811
    busy_week(db, clinic)

    from datetime import date

    report = weekly(db, date.today())  # payments are dated today

    assert (report.deposits_cents, report.desk_cents, report.refunds_cents) == (2000, 6000, 2000)
    assert report.revenue_cents == 6000


def test_any_day_gives_its_week():
    monday = next_monday()

    assert monday_of(monday + timedelta(days=6)) == monday


def test_admin_reads_the_report_without_patient_names(client, db, clinic, headers):  # noqa: F811
    busy_week(db, clinic)

    response = client.get(
        REPORT, params={"week": str(next_monday() + timedelta(days=2))}, headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["week_start"] == str(next_monday())
    assert body["appointments"] == 5 and body["confirmed"] == 1
    assert "Marie" not in response.text and "Paul" not in response.text


def test_other_roles_cannot_read_reports(client, db):
    desk = make_user(db, "accueil-rapport@example.com", role="front_desk")

    response = client.get(REPORT, headers=as_staff(desk, role="front_desk"))

    assert response.status_code == 403
