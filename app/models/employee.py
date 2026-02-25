"""
Employee & Attendance models — core business domain.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Index, Integer,
                        String)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Employee(Base):
    __tablename__ = "employees"

    id: int = Column(Integer, primary_key=True, index=True)  # type: ignore[assignment]
    name: str = Column(String(200), nullable=False)  # type: ignore[assignment]
    rfid_uid: str = Column(String(64), unique=True, nullable=False, index=True)  # type: ignore[assignment]
    email: str | None = Column(String(320), nullable=True)  # type: ignore[assignment]
    phone: str | None = Column(String(30), nullable=True)  # type: ignore[assignment]
    department: str | None = Column(String(100), nullable=True)  # type: ignore[assignment]
    position: str | None = Column(String(100), nullable=True)  # type: ignore[assignment]
    is_active: bool = Column(Boolean, default=True, server_default="true")  # type: ignore[assignment]
    created_at: datetime = Column(  # type: ignore[assignment]
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    attendances = relationship(
        "Attendance",
        back_populates="employee",
        cascade="all, delete-orphan",
    )


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (Index("ix_attendance_employee_date", "employee_id", "date"),)

    id: int = Column(Integer, primary_key=True, index=True)  # type: ignore[assignment]
    employee_id: int = Column(Integer, ForeignKey("employees.id"), nullable=False)  # type: ignore[assignment]
    rfid_uid: str = Column(String(64), nullable=False)  # type: ignore[assignment]
    event_type: str = Column(String(20), nullable=False)  # type: ignore[assignment]
    # IN | OUT | BREAK_START | BREAK_END
    timestamp: datetime = Column(  # type: ignore[assignment]
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    date: str = Column(String(10), index=True)  # type: ignore[assignment]  # YYYY-MM-DD
    notes: str | None = Column(String(500), nullable=True)  # type: ignore[assignment]

    employee = relationship("Employee", back_populates="attendances")
