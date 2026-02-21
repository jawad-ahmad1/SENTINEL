"""Pydantic schemas for Attendance / Employee / Reports."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, field_validator

_UID_RE = re.compile(r"^[A-Za-z0-9:_-]{2,64}$")


# ── Scan ────────────────────────────────────────────────────────────
class ScanRequest(BaseModel):
    uid: str

    @field_validator("uid")
    @classmethod
    def _uid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("UID must not be empty")
        if not _UID_RE.match(v):
            raise ValueError(
                "UID must be 2-64 alphanumeric chars (colons / hyphens allowed)"
            )
        return v


class ScanResponse(BaseModel):
    success: bool
    event: str
    uid: str
    name: str
    attendance_id: int
    attendance_timestamp: str


# ── Break ───────────────────────────────────────────────────────────
class BreakRequest(BaseModel):
    uid: str

    @field_validator("uid")
    @classmethod
    def _uid(cls, v: str) -> str:
        v = v.strip()
        if not _UID_RE.match(v):
            raise ValueError("Invalid UID")
        return v


# ── Employee ────────────────────────────────────────────────────────
class EmployeeCreate(BaseModel):
    name: str
    rfid_uid: str
    email: str | None = None
    phone: str | None = None
    department: str | None = None
    position: str | None = None

    @field_validator("rfid_uid")
    @classmethod
    def _rfid(cls, v: str) -> str:
        v = v.strip()
        if not _UID_RE.match(v):
            raise ValueError("UID must be 2-64 alphanumeric chars")
        return v

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name must not be empty")
        if len(v) > 200:
            raise ValueError("Name must not exceed 200 characters")
        return v


class EmployeeUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    department: str | None = None
    position: str | None = None


class EmployeeRead(BaseModel):
    id: int
    name: str
    rfid_uid: str
    email: str | None
    phone: str | None
    department: str | None
    position: str | None
    is_active: bool
    created_at: datetime | None

    model_config = {"from_attributes": True}


# ── Attendance ──────────────────────────────────────────────────────
class AttendanceRead(BaseModel):
    id: int
    employee_id: int
    rfid_uid: str
    event_type: str
    timestamp: datetime | None
    date: str | None
    notes: str | None = None
    name: str | None = None  # joined from employee table

    model_config = {"from_attributes": True}


# ── Break Response ─────────────────────────────────────────────────
class BreakResponse(BaseModel):
    success: bool
    event: str
    uid: str
    name: str
    attendance_id: int


# ── Attendance Feed (kiosk) ─────────────────────────────────────────
class AttendanceFeedItem(BaseModel):
    id: int
    employee_id: int
    rfid_uid: str
    event_type: str
    timestamp: str | None
    date: str | None
    name: str


# ── Daily Summary ──────────────────────────────────────────────────
class DailySummaryEmployee(BaseModel):
    employee_id: int
    name: str
    first_in: str | None
    last_out: str | None
    work_hours: float
    total_events: int


class DailySummaryResponse(BaseModel):
    date: str
    total_employees: int
    details: list[DailySummaryEmployee]


# ── Monthly Report ─────────────────────────────────────────────────
class MonthlyEmployee(BaseModel):
    employee_id: int
    name: str
    days_present: int
    total_hours: float
    avg_hours: float


class MonthlyReportResponse(BaseModel):
    year: int
    month: int
    total_working_days: int
    employees: list[MonthlyEmployee]


# ── Analytics ──────────────────────────────────────────────────────
class TrendDay(BaseModel):
    date: str
    unique_employees: int
    total_events: int


class TrendsResponse(BaseModel):
    period_days: int
    trends: list[TrendDay]


class EmployeeDaySummary(BaseModel):
    date: str
    hours: float
    events: int


class EmployeeAnalyticsResponse(BaseModel):
    employee_id: int
    name: str
    department: str | None
    period_days: int
    days_worked: int
    total_hours: float
    avg_hours_per_day: float
    daily_summary: list[EmployeeDaySummary]


# ── Health / Status ────────────────────────────────────────────────
class HealthResponse(BaseModel):
    db: bool
    redis: bool


class StatusResponse(BaseModel):
    total_employees: int
    today_scans: int
    status: str


# ── Generic ────────────────────────────────────────────────────────
class LogoutResponse(BaseModel):
    message: str


class DeleteResponse(BaseModel):
    success: bool
    message: str
