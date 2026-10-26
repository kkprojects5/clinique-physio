"""Application settings, read from environment variables or a .env file.

Secrets (database password, keys) are never written in the code (NFR-02).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Look for .env in the repo root (when running from /api) and in the current folder.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    environment: str = "development"  # development, test or production
    database_url: str

    # Secret used to sign tokens (JWT). Long random value, different per environment.
    jwt_secret: str
    # Key used to encrypt sensitive fields in the database (Fernet / AES).
    field_encryption_key: str

    # Version of the privacy policy the patient accepts at registration (Law 25).
    privacy_policy_version: str = "2026-10"
    # Address of the web app, used to build links in emails.
    web_base_url: str = "http://localhost:5173"
    email_verification_hours: int = 24

    # Login sessions (B-AUTH-02)
    access_token_minutes: int = 10  # short-lived: a stolen access token expires quickly
    refresh_token_days_patient: int = 7
    staff_inactivity_minutes: int = 15  # staff are logged out after 15 min without activity
    # The refresh cookie is only sent over HTTPS when True. False only for local development.
    cookie_secure: bool = True
    cookie_samesite: str = "strict"


settings = Settings()
