import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RequestType = Literal["access", "correction", "deletion"]


class PrivacyRequestIn(BaseModel):
    type: RequestType
    details: str | None = Field(default=None, max_length=1000)


class PrivacyRequestOut(BaseModel):
    id: uuid.UUID
    type: str
    details: str | None
    status: str
    requested_at: datetime
    due_at: datetime  # 30 days after the request
    completed_at: datetime | None
    outcome: str | None


class PrivacyRequestAdminOut(PrivacyRequestOut):
    patient_id: uuid.UUID
    patient_name: str
    email: str
    overdue: bool


class PrivacyRequestUpdate(BaseModel):
    status: Literal["in_progress", "completed", "refused"]
    outcome: str | None = Field(default=None, max_length=2000)


class IncidentIn(BaseModel):
    occurred_at: datetime
    discovered_at: datetime
    description: str = Field(min_length=5, max_length=4000)
    data_categories: str = Field(min_length=2, max_length=500)
    people_affected: int | None = Field(default=None, ge=0, le=1_000_000)
    risk_level: Literal["low", "serious"]
    measures: str = Field(min_length=2, max_length=4000)
    cai_notified_at: datetime | None = None
    persons_notified_at: datetime | None = None


class IncidentUpdate(BaseModel):
    """Only the fields sent are changed."""

    description: str | None = Field(default=None, min_length=5, max_length=4000)
    data_categories: str | None = Field(default=None, min_length=2, max_length=500)
    people_affected: int | None = Field(default=None, ge=0, le=1_000_000)
    risk_level: Literal["low", "serious"] | None = None
    measures: str | None = Field(default=None, min_length=2, max_length=4000)
    cai_notified_at: datetime | None = None
    persons_notified_at: datetime | None = None


class IncidentOut(IncidentIn):
    id: uuid.UUID
    recorded_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    to_notify: list[str]  # "cai" and/or "persons" still to notify (serious risk only)
