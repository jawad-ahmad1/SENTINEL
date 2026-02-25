"""
AbsenceOverride model — admin-set absence categories.

Allows administrators to categorize absent days as:
LEAVE, BUSINESS_TRIP, WORK_FROM_HOME, HALF_DAY, SUPPLIER_VISIT
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (Column, DateTime, ForeignKey, Index, Integer, String,
                        UniqueConstraint)

from app.db.base import Base


class AbsenceOverride(Base):
    __tablename__ = "absence_overrides"
    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="uq_override_emp_date"),
        Index("ix_override_employee_date", "employee_id", "date"),
    )

    id: int = Column(Integer, primary_key=True, index=True)  # type: ignore[assignment]
    employee_id: int = Column(Integer, ForeignKey("employees.id"), nullable=False)  # type: ignore[assignment]
    date: str = Column(String(10), nullable=False)  # type: ignore[assignment]  # YYYY-MM-DD
    status: str = Column(String(30), nullable=False)  # type: ignore[assignment]
    # LEAVE | BUSINESS_TRIP | WORK_FROM_HOME | HALF_DAY | SUPPLIER_VISIT
    notes: str | None = Column(String(500), nullable=True)  # type: ignore[assignment]
    created_by: int = Column(Integer, ForeignKey("users.id"), nullable=False)  # type: ignore[assignment]
    created_at: datetime = Column(  # type: ignore[assignment]
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
