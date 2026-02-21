"""
User model — authentication & role-based access control.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, index=True)  # type: ignore[assignment]
    email: str = Column(String(320), unique=True, nullable=False, index=True)  # type: ignore[assignment]
    hashed_password: str = Column(String(128), nullable=False)  # type: ignore[assignment]
    full_name: str | None = Column(String(200), nullable=True)  # type: ignore[assignment]
    role: str = Column(  # type: ignore[assignment]
        String(20),
        nullable=False,
        default="readonly",
        server_default="readonly",
    )  # admin | manager | kiosk | readonly
    is_active: bool = Column(Boolean, default=True, server_default="true")  # type: ignore[assignment]
    created_at: datetime = Column(  # type: ignore[assignment]
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
