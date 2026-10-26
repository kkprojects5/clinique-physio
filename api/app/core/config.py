"""Application settings, read from environment variables or a .env file.

Secrets (database password, keys) are never written in the code (NFR-02).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Look for .env in the repo root (when running from /api) and in the current folder.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str


settings = Settings()
