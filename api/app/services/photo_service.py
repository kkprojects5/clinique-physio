"""Therapist photos on the team page (B-AVL-05).

An uploaded file is never stored or served as it came. It is opened as an image (JPEG, PNG or
WebP only), turned upright, cropped to a square, resized to 400 x 400 and saved again as a new
JPEG. This removes everything else the file held: location and camera details (EXIF), hidden
scripts or a second file disguised as an image.
"""

import io
import uuid
from datetime import UTC, datetime

from fastapi import Request
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.models import Therapist, User
from app.services import audit_service

MAX_BYTES = 3 * 1024 * 1024  # 3 MB uploaded
SIZE = 400  # pixels, square
ACCEPTED = {"JPEG", "PNG", "WEBP"}
CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
Image.MAX_IMAGE_PIXELS = 40_000_000  # refuses "decompression bombs" (huge images in small files)


class PhotoError(Exception):
    """The file is refused (HTTP 422)."""


class NotFound(Exception):
    pass


def clean(data: bytes) -> bytes:
    """A safe 400 x 400 JPEG made from the uploaded image, or PhotoError."""
    if not data:
        raise PhotoError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise PhotoError("The photo must be 3 MB or less.")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            kind = probe.format
            probe.verify()  # checks the file structure without decoding everything
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            picture = ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
        raise PhotoError("The file is not a valid image.") from None
    if kind not in ACCEPTED:
        raise PhotoError("Use a JPEG, PNG or WebP image.")
    square = ImageOps.fit(picture, (SIZE, SIZE), method=Image.Resampling.LANCZOS)
    out = io.BytesIO()
    square.save(out, format="JPEG", quality=85, optimize=True)  # no EXIF: nothing is copied
    return out.getvalue()


def _therapist(db: Session, therapist_id: uuid.UUID) -> Therapist:
    therapist = db.get(Therapist, therapist_id)
    if therapist is None:
        raise NotFound
    return therapist


def set_photo(
    db: Session, admin: User, therapist_id: uuid.UUID, data: bytes, request: Request | None
) -> Therapist:
    therapist = _therapist(db, therapist_id)
    therapist.photo = clean(data)
    therapist.photo_updated_at = datetime.now(UTC)
    audit_service.log(db, admin.id, "update", "therapist_photo", therapist.id, None, request)
    db.commit()
    return therapist


def remove_photo(
    db: Session, admin: User, therapist_id: uuid.UUID, request: Request | None
) -> None:
    therapist = _therapist(db, therapist_id)
    therapist.photo = None
    therapist.photo_updated_at = None
    audit_service.log(db, admin.id, "delete", "therapist_photo", therapist.id, None, request)
    db.commit()


def public_photo(db: Session, therapist_id: uuid.UUID) -> bytes:
    """The photo of an active therapist (a deactivated one leaves the team page)."""
    therapist = db.get(Therapist, therapist_id)
    if therapist is None or therapist.photo is None:
        raise NotFound
    if not db.get(User, therapist.user_id).is_active:
        raise NotFound
    return therapist.photo


def photo_url(therapist: Therapist) -> str | None:
    """Changes when the photo changes, so browsers never show an old one."""
    if therapist.photo_updated_at is None:
        return None
    version = int(therapist.photo_updated_at.timestamp())
    return f"/api/v1/therapists/{therapist.id}/photo?v={version}"
