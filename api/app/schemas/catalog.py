"""Shapes for services, therapists, availability and slots."""

import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, Field, model_validator


class ServiceOut(BaseModel):
    id: uuid.UUID
    name_fr: str
    name_en: str
    description_fr: str | None
    description_en: str | None
    duration_min: int
    price_cents: int
    deposit_cents: int
    is_initial_evaluation: bool
    therapist_ids: list[uuid.UUID]


class TherapistOut(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    specialties: list[str]
    languages: list[str]
    bio_fr: str | None
    bio_en: str | None
    service_ids: list[uuid.UUID]


class SlotOut(BaseModel):
    therapist_id: uuid.UUID
    start: datetime  # UTC
    end: datetime  # UTC
    start_local: str  # clinic time, e.g. "2026-11-02T10:00:00-05:00" (B-BKG-07)


class RuleIn(BaseModel):
    weekday: int = Field(ge=1, le=7)  # 1 = Monday ... 7 = Sunday
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def start_before_end(self) -> "RuleIn":
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class RulesIn(BaseModel):
    rules: list[RuleIn] = Field(max_length=50)

    @model_validator(mode="after")
    def no_overlap_same_day(self) -> "RulesIn":
        by_day: dict[int, list[RuleIn]] = {}
        for rule in self.rules:
            by_day.setdefault(rule.weekday, []).append(rule)
        for rules in by_day.values():
            rules.sort(key=lambda r: r.start_time)
            for a, b in zip(rules, rules[1:], strict=False):
                if b.start_time < a.end_time:
                    raise ValueError("two working periods overlap on the same day")
        return self


class RuleOut(BaseModel):
    weekday: int
    start_time: time
    end_time: time


class ExceptionIn(BaseModel):
    starts_at: datetime
    ends_at: datetime
    reason: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def valid_period(self) -> "ExceptionIn":
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("dates must include a time zone, e.g. 2026-11-02T08:00:00-05:00")
        if self.starts_at >= self.ends_at:
            raise ValueError("starts_at must be before ends_at")
        return self


class ExceptionOut(BaseModel):
    id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    reason: str | None


class AvailabilityOut(BaseModel):
    rules: list[RuleOut]
    exceptions: list[ExceptionOut]


class SlotQuery(BaseModel):
    service_id: uuid.UUID
    therapist_id: uuid.UUID | None = None
    date_from: date
    date_to: date
