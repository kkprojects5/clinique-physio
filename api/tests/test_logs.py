"""Challenge B-C7: no personal or clinical information in the server's logs.

One journey touches every place that logs: registration (email, phone, emergency contact),
emails sent, a SOAP note written and read, a chatbot question with personal details. Every
log line of every logger, at every level, is captured, and none may contain those details.
"""

import logging

import pytest

from tests.test_clinical import SOAP, as_staff, clinic, visit, write_note  # noqa: F401
from tests.test_register import URL as REGISTER
from tests.test_register import valid_payload

EMAIL = "Marie.Tremblay@example.com"
PHONE = "514-555-0142"
CONTACT = "Luc Tremblay 514-555-0199"
NOTE_WORDS = ["Douleur au genou", "Tendinopathie", "Flexion limitée", "excentriques"]


class Capture(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.lines: list[str] = []

    def emit(self, record):
        self.lines.append(self.format(record))


@pytest.fixture
def all_logs():
    """Every logger (the app's, SQLAlchemy's, httpx's...), DEBUG and above."""
    capture = Capture()
    loggers = [logging.getLogger()] + [
        logging.getLogger(name) for name in list(logging.root.manager.loggerDict)
    ]
    saved = [(lg, lg.level, lg.disabled) for lg in loggers]
    for lg in loggers:
        lg.disabled = False
        lg.addHandler(capture)
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger("app").setLevel(logging.DEBUG)
    yield capture.lines
    for lg, level, disabled in saved:
        lg.removeHandler(capture)
        lg.setLevel(level)
        lg.disabled = disabled


def test_no_personal_or_clinical_data_in_any_log(client, db, clinic, all_logs):  # noqa: F811
    registered = client.post(
        REGISTER, json=valid_payload(email=EMAIL, phone=PHONE, emergency_contact=CONTACT)
    )
    appointment = visit(db, clinic, clinic["anne"], clinic["marie"])
    written = write_note(client, clinic["anne"], appointment)
    read = client.get(
        f"/api/v1/therapist/patients/{clinic['marie'].id}/notes",
        headers=as_staff(clinic["anne"]),
    )
    chat = client.post(
        "/api/v1/chat/messages",
        json={"message": f"Je suis {EMAIL}, tél. {PHONE}, où se garer ?", "language": "fr"},
    )

    assert registered.status_code == 202 and written.status_code == 201
    assert read.status_code == 200 and chat.status_code == 200
    text = "\n".join(all_logs)
    assert "email queued" in text  # the log does record that an email left (masked)
    for secret in [EMAIL, EMAIL.lower(), PHONE, "5145550142", CONTACT, *NOTE_WORDS, *SOAP.values()]:
        assert secret not in text, f"found in the logs: {secret!r}"


def test_request_lines_hide_the_query_string():
    """Patient searches (?q=name, phone or birth date) never reach Render's request log."""
    from app.core.logging import HideQueryString

    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("10.0.0.1:5000", "GET", "/api/v1/desk/patients?q=514-555-0142", "1.1", 200),
        None,
    )

    HideQueryString().filter(record)

    line = record.getMessage()
    assert "514-555-0142" not in line
    assert "/api/v1/desk/patients?…" in line


def test_the_filter_is_installed_on_uvicorns_request_log():
    from app.core.logging import HideQueryString, setup_logging

    setup_logging()

    assert any(isinstance(f, HideQueryString) for f in logging.getLogger("uvicorn.access").filters)
