"""Request and response shapes for the authentication endpoints (validated by Pydantic)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

PASSWORD_MIN_LENGTH = 12


class RegisterRequest(BaseModel):
    """Patient registration (B-AUTH-01). Each field is justified in the data dictionary."""

    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    phone: str = Field(pattern=r"^\+?[0-9 ()-]{7,20}$")
    language: Literal["fr", "en"] = "fr"
    emergency_contact: str | None = Field(default=None, max_length=200)
    accept_privacy_policy: bool
    accept_electronic_comms: bool = False

    @field_validator("date_of_birth")
    @classmethod
    def birth_date_in_past(cls, value: date) -> date:
        if value >= date.today() or value.year < 1900:
            raise ValueError("date_of_birth must be a real date in the past")
        return value

    @field_validator("accept_privacy_policy")
    @classmethod
    def privacy_policy_required(cls, value: bool) -> bool:
        if not value:
            raise ValueError("the privacy policy must be accepted to create an account")
        return value

    @model_validator(mode="after")
    def password_not_email(self) -> "RegisterRequest":
        if self.email.split("@")[0].lower() in self.password.lower():
            raise ValueError("the password must not contain the email address")
        return self


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1, max_length=2000)


class MessageResponse(BaseModel):
    message: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    # "bearer" is the standard OAuth 2 token type name, not a secret.
    token_type: str = "bearer"  # noqa: S105
    expires_in: int  # seconds


class MeResponse(BaseModel):
    id: str
    email: str
    role: str
    language: str
    email_verified: bool
