"""
Reporting & analytics endpoints.

All N+1 queries from the old codebase are fixed — each endpoint
fetches all events in **one** SQL query and aggregates in Python.
"""

from __future__ import annotations

import calendar
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

from app.api.v1.deps import get_current_active_user, get_db
from app.models.employee import Attendance, Employee
from app.models.user import User
from app.schemas.attendance import (
    AttendanceFeedItem,
    DailySummaryResponse,
    EmployeeAnalyticsResponse,
    HealthResponse,
    MonthlyReportResponse,
    StatusResponse,
    TrendsResponse,
)

router = APIRouter(tags=["reports"])
logger = logging.getLogger(__name__)


# ── Helpers ─────────────────────────────────────────────────────────
def _ensure_utc(dt: datetime | None) -> datetime:
    """Normalise a potentially-naive timestamp to UTC-aware."""
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _calc_duration(events: list[Attendance]) -> float:
    """Calculate net work hours from a list of events for one employee-day.

    Addresses the 'Overnight Shift' bug by NOT assuming an open session
    ends 'now' if it's in the past. It only counts closed sessions.
    
    If a session is 'IN' but no 'OUT', it is considered 0 hours for that segment
    to avoid 'Infinite Hours' bug. The OUT will be captured on the next day's logic
    if we implement shift linking, but for simple 'Daily' reports, we must be conservative.
    """
    work_secs = 0.0
    break_secs = 0.0
    current_in: datetime | None = None
    current_break: datetime | None = None

    for ev in events:
        ts = _ensure_utc(ev.timestamp)
        if ev.event_type == "IN":
            current_in = ts
        elif ev.event_type == "OUT":
            if current_in:
                work_secs += (ts - current_in).total_seconds()
                current_in = None
        elif ev.event_type == "BREAK_START":
            current_break = ts
        elif ev.event_type == "BREAK_END":
            if current_break:
                break_secs += (ts - current_break).total_seconds()
                current_break = None

    # Unpaired IN events (missed clock-out) are ignored for safety.
    return round(max(0.0, (work_secs - break_secs)) / 3600, 2)


# ── Today (PUBLIC — kiosk feed) ─────────────────────────────────────
@router.get("/attendance/today", response_model=list[AttendanceFeedItem])
async def attendance_today(
    db: AsyncSession = Depends(get_db),
) -> list[AttendanceFeedItem]:
    """Return today's attendance events for the kiosk live feed."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = await db.execute(
        select(Attendance, Employee.name)
        .join(Employee, Attendance.employee_id == Employee.id)
        .where(Attendance.date == today_str)
        .order_by(Attendance.timestamp.desc())
    )
    return [
        {
            "id": att.id,
            "employee_id": att.employee_id,
            "rfid_uid": att.rfid_uid,
            "event_type": att.event_type,
            "timestamp": att.timestamp.isoformat() if att.timestamp else None,
            "date": att.date,
            "name": name,
        }
        for att, name in result.all()
    ]


# ── Daily Summary (N+1 FIXED — single query) ───────────────────────
@router.get("/reports/summary/{date_str}", response_model=DailySummaryResponse)
async def reports_summary(
    date_str: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
) -> DailySummaryResponse:
    """Generate a daily summary with work hours per employee."""
    result = await db.execute(
        select(Attendance, Employee.name)
        .join(Employee, Attendance.employee_id == Employee.id)
        .where(Attendance.date == date_str)
        .order_by(Attendance.employee_id, Attendance.timestamp.asc())
    )
    rows = result.all()

    by_employee: dict[int, list[Attendance]] = defaultdict(list)
    names: dict[int, str] = {}
    for att, name in rows:
        by_employee[att.employee_id].append(att)
        names[att.employee_id] = name

    details = []
    for emp_id, events in by_employee.items():
        first_in = next(
            (e.timestamp.isoformat() for e in events if e.event_type == "IN"),
            None,
        )
        last_out = next(
            (
                e.timestamp.isoformat()
                for e in reversed(events)
                if e.event_type == "OUT"
            ),
            None,
        )
        details.append(
            {
                "employee_id": emp_id,
                "name": names[emp_id],
                "first_in": first_in,
                "last_out": last_out,
                "work_hours": _calc_duration(events),
                "total_events": len(events),
            }
        )

    return DailySummaryResponse(
        date=date_str, total_employees=len(details), details=details
    )


# ── Daily CSV ─────────────────────────────────────────────────────
@router.get("/reports/daily/csv")
async def daily_csv(
    date_str: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Export daily attendance as a CSV file download."""
    result = await db.execute(
        select(Attendance, Employee.name)
        .join(Employee, Attendance.employee_id == Employee.id)
        .where(Attendance.date == date_str)
        .order_by(Attendance.employee_id, Attendance.timestamp.asc())
    )
    rows = result.all()

    by_emp: dict[int, list[Attendance]] = defaultdict(list)
    names: dict[int, str] = {}
    for att, name in rows:
        by_emp[att.employee_id].append(att)
        names[att.employee_id] = name

    def iter_csv():
        yield "employee_id,name,date,first_in,last_out,work_hours\n"
        for emp_id, events in by_emp.items():
            first_in = next(
                (e.timestamp.isoformat() for e in events if e.event_type == "IN"), ""
            )
            last_out = next(
                (
                    e.timestamp.isoformat()
                    for e in reversed(events)
                    if e.event_type == "OUT"
                ),
                "",
            )
            yield f"{emp_id},{names[emp_id]},{date_str},{first_in},{last_out},{_calc_duration(events)}\n"

    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=attendance_{date_str}.csv"
        },
    )


def _count_weekdays(year: int, month: int) -> int:
    """Count business days (Mon-Fri) in a given month."""
    _, days_in_month = calendar.monthrange(year, month)
    count = 0
    for day in range(1, days_in_month + 1):
        if date(year, month, day).weekday() < 5:  # Mon=0 .. Fri=4
            count += 1
    return count


# ── Monthly Report (N+1 FIXED — single query) ──────────────────────
@router.get("/reports/monthly/{year}/{month}", response_model=MonthlyReportResponse)
async def monthly_report(
    year: int,
    month: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
) -> MonthlyReportResponse:
    """Generate a monthly attendance summary per employee."""
    _, days_in_month = calendar.monthrange(year, month)
    start = f"{year:04d}-{month:02d}-01"
    end = f"{year:04d}-{month:02d}-{days_in_month:02d}"

    result = await db.execute(
        select(Attendance, Employee.name)
        .join(Employee, Attendance.employee_id == Employee.id)
        .where(Attendance.date >= start, Attendance.date <= end)
        .order_by(Attendance.employee_id, Attendance.timestamp.asc())
    )
    rows = result.all()

    by_emp: dict[int, dict[str, list[Attendance]]] = defaultdict(
        lambda: defaultdict(list)
    )
    names: dict[int, str] = {}
    for att, name in rows:
        by_emp[att.employee_id][att.date].append(att)
        names[att.employee_id] = name

    employees = []
    for emp_id, dates in by_emp.items():
        total_hours = sum(_calc_duration(evts) for evts in dates.values())
        employees.append(
            {
                "employee_id": emp_id,
                "name": names[emp_id],
                "days_present": len(dates),
                "total_hours": round(total_hours, 2),
                "avg_hours": round(total_hours / max(1, len(dates)), 2),
            }
        )

    return MonthlyReportResponse(
        year=year,
        month=month,
        total_working_days=_count_weekdays(year, month),
        employees=employees,
    )


# ── Trends (single aggregate query) ────────────────────────────────
@router.get("/analytics/trends", response_model=TrendsResponse)
async def analytics_trends(
    days: int = Query(default=30, le=90),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
) -> TrendsResponse:
    """Return attendance trends over the last N days."""
    start = (date.today() - timedelta(days=days)).isoformat()

    result = await db.execute(
        select(
            Attendance.date,
            func.count(func.distinct(Attendance.employee_id)).label(
                "unique_employees"
            ),
            func.count(Attendance.id).label("total_events"),
        )
        .where(Attendance.date >= start)
        .group_by(Attendance.date)
        .order_by(Attendance.date.desc())
    )

    return TrendsResponse(
        period_days=days,
        trends=[
            {
                "date": r.date,
                "unique_employees": r.unique_employees,
                "total_events": r.total_events,
            }
            for r in result.all()
        ],
    )


# ── Employee Analytics (N+1 FIXED — single query for 30 days) ──────
@router.get("/analytics/employee/{employee_id}", response_model=EmployeeAnalyticsResponse)
async def employee_analytics(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
) -> EmployeeAnalyticsResponse:
    """Return 30-day attendance analytics for a specific employee."""
    emp_result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = emp_result.scalar_one_or_none()
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    today = date.today()
    start = (today - timedelta(days=30)).isoformat()

    result = await db.execute(
        select(Attendance)
        .where(
            Attendance.employee_id == employee_id,
            Attendance.date >= start,
            Attendance.date <= today.isoformat(),
        )
        .order_by(Attendance.timestamp.asc())
    )
    all_events = result.scalars().all()

    by_date: dict[str, list[Attendance]] = defaultdict(list)
    for ev in all_events:
        by_date[ev.date].append(ev)

    daily: list[dict] = []
    total_hours = 0.0
    days_worked = 0
    for i in range(30):
        ds = (today - timedelta(days=i)).isoformat()
        day_events = by_date.get(ds, [])
        hours = _calc_duration(day_events) if day_events else 0.0
        if hours > 0:
            days_worked += 1
            total_hours += hours
        daily.append({"date": ds, "hours": hours, "events": len(day_events)})

    return EmployeeAnalyticsResponse(
        employee_id=employee_id,
        name=employee.name,
        department=employee.department,
        period_days=30,
        days_worked=days_worked,
        total_hours=round(total_hours, 2),
        avg_hours_per_day=round(total_hours / max(1, days_worked), 2),
        daily_summary=daily,
    )


# ── Health / Status ─────────────────────────────────────────────────
@router.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Public health check — DB and Redis connectivity."""
    result = HealthResponse(db=False, redis=False)

    try:
        await db.execute(select(1))
        result.db = True
    except Exception as e:
        logger.error("Health check DB failure: %s", e)

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
        result.redis = True
    except Exception as e:
        logger.error("Health check Redis failure: %s", e)

    return result


@router.get("/status", response_model=StatusResponse)
async def system_status(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
) -> StatusResponse:
    """Return current system status — employee count and today's scans."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    emp_count = await db.execute(
        select(func.count(Employee.id)).where(Employee.is_active.is_(True))
    )
    scan_count = await db.execute(
        select(func.count(Attendance.id)).where(Attendance.date == today_str)
    )

    return StatusResponse(
        total_employees=emp_count.scalar() or 0,
        today_scans=scan_count.scalar() or 0,
        status="operational",
    )
