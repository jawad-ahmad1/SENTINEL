"""
Attendance Settings model — singleton table for admin-configurable rules.

Only one row should ever exist. The admin updates it via the settings API,
and the scan / reports logic reads it to determine late arrivals, work hours, etc.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from app.db.base import Base


class AttendanceSettings(Base):
    __tablename__ = "attendance_settings"

    id: int = Column(Integer, primary_key=True, default=1)  # type: ignore[assignment]
    work_start: str = Column(String(5), nullable=False, default="09:00")  # type: ignore[assignment]
    work_end: str = Column(String(5), nullable=False, default="17:00")  # type: ignore[assignment]
    grace_minutes: int = Column(Integer, nullable=False, default=15)  # type: ignore[assignment]
    allowed_absent: int = Column(Integer, nullable=False, default=5)  # type: ignore[assignment]
    allowed_leave: int = Column(Integer, nullable=False, default=10)  # type: ignore[assignment]
    allowed_half_day: int = Column(Integer, nullable=False, default=5)  # type: ignore[assignment]
    timezone_offset: str = Column(String(6), nullable=False, default="+05:00")  # type: ignore[assignment]
    updated_at: datetime = Column(  # type: ignore[assignment]
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
