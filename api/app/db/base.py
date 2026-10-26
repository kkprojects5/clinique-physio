"""Base class for all SQLAlchemy models."""

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    # Every datetime column is "timestamptz": stored in UTC (B-BKG-07).
    type_annotation_map = {datetime: DateTime(timezone=True)}
