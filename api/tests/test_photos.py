"""Therapist photos on the team page (B-AVL-05)."""

import io
import uuid

import pytest
from PIL import Image
from sqlalchemy import select

from app.models import AuditLog, User
from app.services import photo_service
from tests.test_booking import clinic  # noqa: F401  (fixture)
from tests.test_clinical import as_staff
from tests.test_login import make_user
from tests.test_privacy import admin, headers  # noqa: F401  (fixtures)


def image(kind="PNG", size=(800, 600), exif=False) -> bytes:
    out = io.BytesIO()
    picture = Image.new("RGB", size, (31, 94, 88))
    if exif:
        data = Image.Exif()
        data[0x010F] = "SecretCamera"  # Make
        data[0x8825] = {2: (45.0, 30.0, 0.0)}  # GPS latitude
        picture.save(out, format=kind, exif=data)
    else:
        picture.save(out, format=kind)
    return out.getvalue()


def upload(client, therapist, headers, data, kind="image/png"):  # noqa: F811
    return client.put(
        f"/api/v1/admin/therapists/{therapist.id}/photo",
        content=data,
        headers={**headers, "Content-Type": kind},
    )


# --- Cleaning the image -------------------------------------------------------------------------


def test_photo_is_resized_to_a_square_jpeg():
    cleaned = photo_service.clean(image(size=(1200, 800)))

    with Image.open(io.BytesIO(cleaned)) as result:
        assert result.format == "JPEG"
        assert result.size == (400, 400)


def test_location_and_camera_details_are_removed():
    cleaned = photo_service.clean(image(kind="JPEG", exif=True))

    with Image.open(io.BytesIO(cleaned)) as result:
        assert len(result.getexif()) == 0
    assert b"SecretCamera" not in cleaned


@pytest.mark.parametrize(
    "data",
    [b"", b"<script>alert(1)</script>", b"%PDF-1.4 not an image", b"GIF89a" + b"\x00" * 50],
)
def test_files_that_are_not_valid_images_are_refused(data):
    with pytest.raises(photo_service.PhotoError):
        photo_service.clean(data)


def test_gif_is_refused_even_when_valid():
    with pytest.raises(photo_service.PhotoError, match="JPEG, PNG or WebP"):
        photo_service.clean(image(kind="GIF"))


def test_too_large_file_is_refused():
    with pytest.raises(photo_service.PhotoError, match="3 MB"):
        photo_service.clean(b"x" * (photo_service.MAX_BYTES + 1))


# --- Administrator upload -----------------------------------------------------------------------


def test_admin_uploads_and_the_team_page_shows_it(client, db, clinic, headers):  # noqa: F811
    anne = clinic["anne"]

    response = upload(client, anne, headers, image())

    assert response.status_code == 200
    url = response.json()["photo_url"]
    assert url.startswith(f"/api/v1/therapists/{anne.id}/photo?v=")
    team = client.get("/api/v1/therapists").json()
    assert next(t for t in team if t["id"] == str(anne.id))["photo_url"] == url
    photo = client.get(url)
    assert photo.status_code == 200
    assert photo.headers["content-type"] == "image/jpeg"
    assert photo.headers["x-content-type-options"] == "nosniff"
    assert photo.content.startswith(b"\xff\xd8")
    assert db.scalar(select(AuditLog).where(AuditLog.resource_type == "therapist_photo"))


def test_wrong_content_type_is_refused(client, clinic, headers):  # noqa: F811
    response = upload(client, clinic["anne"], headers, b"<svg onload=alert(1)>", "image/svg+xml")

    assert response.status_code == 415


def test_fake_image_is_refused(client, clinic, headers):  # noqa: F811
    response = upload(client, clinic["anne"], headers, b"<html>not a png</html>")

    assert response.status_code == 422


def test_admin_removes_the_photo(client, clinic, headers):  # noqa: F811
    anne = clinic["anne"]
    upload(client, anne, headers, image())

    removed = client.delete(f"/api/v1/admin/therapists/{anne.id}/photo", headers=headers)

    assert removed.status_code == 204
    assert client.get(f"/api/v1/therapists/{anne.id}/photo").status_code == 404
    staff = client.get("/api/v1/admin/staff", headers=headers).json()
    assert next(m for m in staff if m["therapist_id"] == str(anne.id))["photo_url"] is None


def test_unknown_therapist(client, headers):  # noqa: F811
    assert upload(client, type("T", (), {"id": uuid.uuid4()}), headers, image()).status_code == 404


def test_deactivated_therapist_photo_is_hidden(client, db, clinic, headers):  # noqa: F811
    anne = clinic["anne"]
    upload(client, anne, headers, image())
    db.get(User, anne.user_id).is_active = False
    db.commit()

    assert client.get(f"/api/v1/therapists/{anne.id}/photo").status_code == 404


@pytest.mark.parametrize("role", ["therapist", "front_desk"])
def test_only_the_administrator_changes_photos(client, db, clinic, role):  # noqa: F811
    user = make_user(db, f"{role}-{uuid.uuid4().hex[:6]}@example.com", role=role)

    response = upload(client, clinic["anne"], as_staff(user, role=role), image())

    assert response.status_code == 403
