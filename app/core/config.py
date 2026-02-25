"""
Centralised application settings loaded from environment / .env file.

Uses pydantic-settings so every value can be overridden via env vars
or the .env file at the project root.
"""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Project ──────────────────────────────────────────────────────
    PROJECT_NAME: str = "RFID Attendance System"
    VERSION: str = "2.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # ── Database (async PostgreSQL via asyncpg) ─────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://attendance:attendance@localhost:5432/attendance_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ──────────────────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE-ME-TO-A-RANDOM-64-CHAR-HEX-STRING-IN-PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BOUNCE_WINDOW_SECONDS: int = 2
    COOKIE_SECURE: bool = False  # Set True in HTTPS production

    # ── CORS ─────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost",
        "http://localhost:80",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:80",
        "http://127.0.0.1:8000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v  # type: ignore[return-value]

    # ── Logging ──────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── Default admin (seeded on first startup) ─────────────────────
    FIRST_ADMIN_EMAIL: str = "admin@attendance.local"
    FIRST_ADMIN_PASSWORD: str = "changeme123"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()

if settings.SECRET_KEY == "CHANGE-ME-TO-A-RANDOM-64-CHAR-HEX-STRING-IN-PRODUCTION":
    import logging

    logging.getLogger("app.core.config").warning(
        "⚠️  WARNING: You are running with the default INSECURE Secret Key! "
        "Update the SECRET_KEY in your .env file immediately."
    )
