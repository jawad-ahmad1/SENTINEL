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
from fastapi.responses import StreamingResponse
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_active_user, get_db, require_admin
from app.core.config import settings
from app.models.absence_override import AbsenceOverride
from app.models.attendance_settings import AttendanceSettings
from app.models.employee import Attendance, Employee
from app.models.user import User
from app.schemas.attendance import (VALID_OVERRIDE_STATUSES, AbsenceDayDetail,
                                    AbsenceEmployeeDetail,
                                    AbsenceOverrideCreate, AbsenceOverrideRead,
                                    AbsenceReportResponse, AttendanceFeedItem,
                                    DailySummaryResponse,
                                    EmployeeAnalyticsResponse,
                                    EmployeeMonthAbsence, HealthResponse,
                                    LiveStatsResponse, MonthlyReportResponse,
                                    StatusResponse, TrendsResponse)

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

    def _fmt_time(ts):
        """Format a timestamp to readable HH:MM AM/PM."""
        if ts is None:
            return ""
        return ts.strftime("%I:%M %p")

    def iter_csv():
        yield "employee_id,name,date,first_in,last_out,work_hours\n"
        for emp_id, events in by_emp.items():
            first_in_ts = next(
                (e.timestamp for e in events if e.event_type == "IN"), None
            )
            last_out_ts = next(
                (e.timestamp for e in reversed(events) if e.event_type == "OUT"),
                None,
            )
            hours = round(_calc_duration(events), 2)
            yield f"{emp_id},{names[emp_id]},{date_str},{_fmt_time(first_in_ts)},{_fmt_time(last_out_ts)},{hours}\n"

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
            func.count(func.distinct(Attendance.employee_id)).label("unique_employees"),
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
@router.get(
    "/analytics/employee/{employee_id}", response_model=EmployeeAnalyticsResponse
)
async def employee_analytics(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
) -> EmployeeAnalyticsResponse:
    """Return 30-day attendance analytics for a specific employee."""
    emp_result = await db.execute(select(Employee).where(Employee.id == employee_id))
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


# ── Monthly Absence Report ──────────────────────────────────────────
@router.get("/reports/absence/{year}/{month}", response_model=AbsenceReportResponse)
async def absence_report(
    year: int,
    month: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
) -> AbsenceReportResponse:
    """Generate a monthly absence report with daily breakdown and employee details."""
    import calendar as cal_mod

    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Month must be 1-12")

    # Get all active employees
    emp_result = await db.execute(
        select(Employee).where(Employee.is_active.is_(True)).order_by(Employee.name)
    )
    employees = list(emp_result.scalars().all())
    total_employees = len(employees)

    if total_employees == 0:
        return AbsenceReportResponse(
            year=year,
            month=month,
            month_name=cal_mod.month_name[month],
            total_working_days=0,
            total_employees=0,
            total_absences=0,
            absence_rate=0.0,
            daily_breakdown=[],
            employee_details=[],
            perfect_attendance=[],
            concerning_absences=[],
        )

    # Determine working days (Mon-Fri) in the month
    _, days_in_month = cal_mod.monthrange(year, month)
    working_days = []
    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        if d.weekday() < 5:  # Mon=0 ... Fri=4
            working_days.append(d)

    # Only include working days up to today (don't count future days as absences)
    today = date.today()
    working_days = [d for d in working_days if d <= today]
    total_working_days = len(working_days)

    if total_working_days == 0:
        return AbsenceReportResponse(
            year=year,
            month=month,
            month_name=cal_mod.month_name[month],
            total_working_days=0,
            total_employees=total_employees,
            total_absences=0,
            absence_rate=0.0,
            daily_breakdown=[],
            employee_details=[],
            perfect_attendance=[e.name for e in employees],
            concerning_absences=[],
        )

    # Fetch ALL attendance for this month in ONE query
    month_start = f"{year}-{month:02d}-01"
    month_end = f"{year}-{month:02d}-{days_in_month:02d}"
    att_result = await db.execute(
        select(Attendance)
        .where(Attendance.date >= month_start, Attendance.date <= month_end)
        .order_by(Attendance.date)
    )
    all_attendance = list(att_result.scalars().all())

    # Build lookup: date_str -> set of employee_ids who attended
    attendance_by_date: dict[str, set[int]] = defaultdict(set)
    for att in all_attendance:
        attendance_by_date[att.date].add(att.employee_id)

    # Build lookup: employee_id -> list of absent dates
    emp_absent_dates: dict[int, list[str]] = defaultdict(list)

    # Compute daily breakdown
    daily_breakdown = []
    total_absences = 0
    for wd in working_days:
        date_str = wd.strftime("%Y-%m-%d")
        present_ids = attendance_by_date.get(date_str, set())
        present = len(present_ids)
        absent = total_employees - present
        total_absences += absent
        absence_rate = (
            round((absent / total_employees) * 100, 1) if total_employees > 0 else 0.0
        )

        daily_breakdown.append(
            AbsenceDayDetail(
                date=date_str,
                day_name=wd.strftime("%A"),
                expected=total_employees,
                present=present,
                absent=absent,
                absence_rate=absence_rate,
            )
        )

        # Track which employees were absent each day
        for emp in employees:
            if emp.id not in present_ids:
                emp_absent_dates[emp.id].append(date_str)

    # Fetch overrides for this month
    override_result = await db.execute(
        select(AbsenceOverride).where(
            AbsenceOverride.date >= month_start, AbsenceOverride.date <= month_end
        )
    )
    overrides_list = override_result.scalars().all()
    # Build lookup: {employee_id: {date: status}}
    override_map: dict[int, dict[str, str]] = defaultdict(dict)
    for ov in overrides_list:
        override_map[ov.employee_id][ov.date] = ov.status

    # Statuses that count as "working" — not absent
    WORKING_OVERRIDES = {"WORK_FROM_HOME", "BUSINESS_TRIP", "SUPPLIER_VISIT"}

    # Fetch settings for concerning thresholds
    conf_result = await db.execute(select(AttendanceSettings).limit(1))
    settings_obj = conf_result.scalar_one_or_none()
    limit_absent = settings_obj.allowed_absent if settings_obj else 5
    limit_leave = settings_obj.allowed_leave if settings_obj else 10
    limit_half_day = settings_obj.allowed_half_day if settings_obj else 5

    # Employee absence details — recalculate real absences based on overrides
    employee_details = []
    perfect_attendance = []
    concerning_absences = []
    adjusted_total_absences = 0

    for emp in employees:
        absent_dates = emp_absent_dates.get(emp.id, [])
        if len(absent_dates) == 0:
            perfect_attendance.append(emp.name)
            continue

        emp_overrides = {
            d: override_map[emp.id][d]
            for d in absent_dates
            if d in override_map.get(emp.id, {})
        }

        # Calculate real absence days: skip working overrides, separate leaves and half days
        real_absent = 0.0
        real_leave = 0.0
        real_half_day = 0.0
        for d in absent_dates:
            status = emp_overrides.get(d)
            if status in WORKING_OVERRIDES:
                continue  # Not absent — working remotely/on trip
            elif status == "HALF_DAY":
                real_half_day += 1.0
            elif status == "LEAVE":
                real_leave += 1.0
            else:
                real_absent += 1.0  # ABSENT or no override

        adjusted_total_absences += real_absent

        if real_absent == 0 and real_half_day == 0 and real_leave == 0:
            perfect_attendance.append(emp.name)
        else:
            detail = AbsenceEmployeeDetail(
                employee_id=emp.id,
                name=emp.name,
                department=emp.department,
                days_absent=real_absent,
                days_leave=real_leave,
                days_half_day=real_half_day,
                dates_absent=absent_dates,
                overrides=emp_overrides,
            )
            employee_details.append(detail)

            # Concerning if they meet or exceed (threshold - 1)
            is_concerning = False
            if real_absent > 0 and real_absent >= max(1, limit_absent - 1):
                is_concerning = True
            elif real_leave > 0 and real_leave >= max(1, limit_leave - 1):
                is_concerning = True
            elif real_half_day > 0 and real_half_day >= max(1, limit_half_day - 1):
                is_concerning = True

            if is_concerning:
                concerning_absences.append(detail)

    # Sort employee details by most absences first
    employee_details.sort(key=lambda x: x.days_absent, reverse=True)
    concerning_absences.sort(key=lambda x: x.days_absent, reverse=True)

    overall_absence_rate = (
        round(
            (adjusted_total_absences / (total_employees * total_working_days)) * 100, 1
        )
        if (total_employees * total_working_days) > 0
        else 0.0
    )

    return AbsenceReportResponse(
        year=year,
        month=month,
        month_name=cal_mod.month_name[month],
        total_working_days=total_working_days,
        total_employees=total_employees,
        total_absences=adjusted_total_absences,
        absence_rate=overall_absence_rate,
        daily_breakdown=daily_breakdown,
        employee_details=employee_details,
        perfect_attendance=perfect_attendance,
        concerning_absences=concerning_absences,
    )


# ── Live Stats (PUBLIC — kiosk idle screen) ─────────────────────────
@router.get("/attendance/live-stats", response_model=LiveStatsResponse)
async def live_stats(
    db: AsyncSession = Depends(get_db),
) -> LiveStatsResponse:
    """Real-time attendance counts for the kiosk idle screen and admin dashboard."""

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Total active employees
    emp_result = await db.execute(
        select(func.count(Employee.id)).where(Employee.is_active.is_(True))
    )
    total_employees = emp_result.scalar() or 0

    # Today's scan count
    scan_result = await db.execute(
        select(func.count(Attendance.id)).where(Attendance.date == today_str)
    )
    today_scans = scan_result.scalar() or 0

    # Fetch all today's attendance in one query
    att_result = await db.execute(
        select(Attendance)
        .where(Attendance.date == today_str)
        .order_by(Attendance.employee_id, Attendance.timestamp.asc())
    )
    all_today = list(att_result.scalars().all())

    # Group by employee — determine who is currently IN (last event = IN)

    employee_events: dict[int, list[Attendance]] = defaultdict(list)
    for att in all_today:
        employee_events[att.employee_id].append(att)

    present = 0
    late = 0
    on_time = 0

    # Read attendance settings for late calculation
    work_start = "09:00"
    grace_minutes = 15
    tz_offset = "+05:00"
    try:
        settings_result = await db.execute(select(AttendanceSettings).limit(1))
        att_settings = settings_result.scalar_one_or_none()
        if att_settings:
            work_start = att_settings.work_start
            grace_minutes = att_settings.grace_minutes
            tz_offset = att_settings.timezone_offset
    except Exception:
        pass

    for emp_id, events in employee_events.items():
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        last_event = sorted_events[-1]
        if last_event.event_type == "IN":
            present += 1

        # Check if first IN was late
        first_in = next((e for e in sorted_events if e.event_type == "IN"), None)
        if first_in:
            ts = first_in.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            sign = 1 if tz_offset[0] == "+" else -1
            offset_parts = tz_offset[1:].split(":")
            offset_hours = int(offset_parts[0])
            offset_mins = int(offset_parts[1]) if len(offset_parts) > 1 else 0
            local_offset = timedelta(
                hours=sign * offset_hours, minutes=sign * offset_mins
            )
            local_tz = timezone(local_offset)
            local_time = ts.astimezone(local_tz)

            start_parts = work_start.split(":")
            start_hour, start_min = int(start_parts[0]), int(start_parts[1])
            cutoff = local_time.replace(
                hour=start_hour, minute=start_min, second=0, microsecond=0
            ) + timedelta(minutes=grace_minutes)

            if local_time > cutoff:
                late += 1
            else:
                on_time += 1

    absent = max(0, total_employees - len(employee_events))

    return LiveStatsResponse(
        total_employees=total_employees,
        present=present,
        absent=absent,
        late=late,
        on_time=on_time,
        today_scans=today_scans,
    )


# ── Clear Attendance Records (ADMIN-ONLY) ───────────────────────────
@router.delete("/attendance/clear")
async def clear_attendance(
    scope: str = Query(default="all", description="Scope: all, date, range, employee"),
    date_str: str | None = Query(
        default=None, description="Date (YYYY-MM-DD) for scope=date"
    ),
    date_from: str | None = Query(
        default=None, description="Start date for scope=range"
    ),
    date_to: str | None = Query(default=None, description="End date for scope=range"),
    employee_id: int | None = Query(
        default=None, description="Employee ID for scope=employee"
    ),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Admin-only: Delete attendance records by scope.

    Scopes:
      - all: Delete ALL attendance records
      - date: Delete records for a specific date  (requires date_str)
      - range: Delete records in a date range      (requires date_from, date_to)
      - employee: Delete records for an employee   (requires employee_id)
    """
    stmt = sa_delete(Attendance)

    if scope == "date":
        if not date_str:
            raise HTTPException(
                status_code=400, detail="date_str required for scope=date"
            )
        stmt = stmt.where(Attendance.date == date_str)
    elif scope == "range":
        if not date_from or not date_to:
            raise HTTPException(
                status_code=400, detail="date_from and date_to required for scope=range"
            )
        stmt = stmt.where(Attendance.date >= date_from, Attendance.date <= date_to)
    elif scope == "employee":
        if not employee_id:
            raise HTTPException(
                status_code=400, detail="employee_id required for scope=employee"
            )
        stmt = stmt.where(Attendance.employee_id == employee_id)
    elif scope != "all":
        raise HTTPException(status_code=400, detail=f"Unknown scope: {scope}")

    result = await db.execute(stmt)
    await db.commit()
    deleted = result.rowcount

    logger.warning("ADMIN cleared %d attendance records (scope=%s)", deleted, scope)

    return {"success": True, "deleted": deleted, "scope": scope}


# ── Absence Override CRUD (ADMIN-ONLY) ──────────────────────────────
@router.post("/attendance/absence-override")
async def create_absence_override(
    body: AbsenceOverrideCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Create or update an absence override for a specific employee and date."""
    if body.status not in VALID_OVERRIDE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(VALID_OVERRIDE_STATUSES)}",
        )

    # Check if override already exists — upsert
    existing = await db.execute(
        select(AbsenceOverride).where(
            AbsenceOverride.employee_id == body.employee_id,
            AbsenceOverride.date == body.date,
        )
    )
    override = existing.scalar_one_or_none()

    if override:
        override.status = body.status
        override.notes = body.notes
        override.created_by = admin.id
    else:
        override = AbsenceOverride(
            employee_id=body.employee_id,
            date=body.date,
            status=body.status,
            notes=body.notes,
            created_by=admin.id,
        )
        db.add(override)

    await db.commit()
    await db.refresh(override)

    return {
        "id": override.id,
        "employee_id": override.employee_id,
        "date": override.date,
        "status": override.status,
        "notes": override.notes,
    }


@router.get("/attendance/absence-overrides")
async def list_absence_overrides(
    employee_id: int | None = Query(default=None),
    month: str | None = Query(default=None, description="YYYY-MM"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """List absence overrides with optional filters."""
    stmt = (
        select(AbsenceOverride, Employee.name)
        .join(Employee, AbsenceOverride.employee_id == Employee.id)
        .order_by(AbsenceOverride.date.desc())
    )

    if employee_id:
        stmt = stmt.where(AbsenceOverride.employee_id == employee_id)
    if month:
        stmt = stmt.where(AbsenceOverride.date.startswith(month))

    result = await db.execute(stmt)
    rows = result.all()

    return [
        AbsenceOverrideRead(
            id=ov.id,
            employee_id=ov.employee_id,
            employee_name=name,
            date=ov.date,
            status=ov.status,
            notes=ov.notes,
            created_by=ov.created_by,
            created_at=ov.created_at.isoformat() if ov.created_at else None,
        )
        for ov, name in rows
    ]


@router.delete("/attendance/absence-override/{override_id}")
async def delete_absence_override(
    override_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Delete a specific absence override."""
    result = await db.execute(
        select(AbsenceOverride).where(AbsenceOverride.id == override_id)
    )
    override = result.scalar_one_or_none()
    if not override:
        raise HTTPException(status_code=404, detail="Override not found")

    await db.delete(override)
    await db.commit()
    return {"success": True, "deleted_id": override_id}


# ── Per-Employee Absence Detail ─────────────────────────────────────
@router.get(
    "/reports/absence/{year}/{month}/employee/{employee_id}",
    response_model=EmployeeMonthAbsence,
)
async def employee_absence_detail(
    year: int,
    month: int,
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
) -> EmployeeMonthAbsence:
    """Get absence details for a single employee in a given month."""
    import calendar as cal_mod

    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Month must be 1-12")

    # Get employee
    emp_result = await db.execute(select(Employee).where(Employee.id == employee_id))
    emp = emp_result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Working days
    _, days_in_month = cal_mod.monthrange(year, month)
    working_days = []
    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        if d.weekday() < 5:
            working_days.append(d)

    today = date.today()
    working_days = [d for d in working_days if d <= today]
    total_working = len(working_days)

    # Attendance for this employee this month
    month_start = f"{year}-{month:02d}-01"
    month_end = f"{year}-{month:02d}-{days_in_month:02d}"
    att_result = await db.execute(
        select(Attendance).where(
            Attendance.employee_id == employee_id,
            Attendance.date >= month_start,
            Attendance.date <= month_end,
            Attendance.event_type == "IN",
        )
    )
    present_dates = {a.date for a in att_result.scalars().all()}

    absent_dates = [
        d.strftime("%Y-%m-%d")
        for d in working_days
        if d.strftime("%Y-%m-%d") not in present_dates
    ]

    # Overrides
    ov_result = await db.execute(
        select(AbsenceOverride).where(
            AbsenceOverride.employee_id == employee_id,
            AbsenceOverride.date >= month_start,
            AbsenceOverride.date <= month_end,
        )
    )
    overrides = {ov.date: ov.status for ov in ov_result.scalars().all()}

    # Calculate real absences considering overrides
    WORKING_OVERRIDES = {"WORK_FROM_HOME", "BUSINESS_TRIP", "SUPPLIER_VISIT"}
    real_absent = 0.0
    real_leave = 0.0
    real_half_day = 0.0
    for d in absent_dates:
        status = overrides.get(d)
        if status in WORKING_OVERRIDES:
            continue  # Working day
        elif status == "HALF_DAY":
            real_half_day += 1.0
        elif status == "LEAVE":
            real_leave += 1.0
        else:
            real_absent += 1.0

    days_present = total_working - real_absent - real_leave - real_half_day
    attendance_rate = (
        round((days_present / total_working) * 100, 1) if total_working > 0 else 0.0
    )

    return EmployeeMonthAbsence(
        employee_id=emp.id,
        name=emp.name,
        department=emp.department,
        year=year,
        month=month,
        month_name=cal_mod.month_name[month],
        working_days=total_working,
        days_present=float(days_present),
        days_absent=float(real_absent),
        days_leave=float(real_leave),
        days_half_day=float(real_half_day),
        dates_absent=absent_dates,
        overrides=overrides,
        attendance_rate=attendance_rate,
    )
