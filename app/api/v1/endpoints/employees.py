"""
Employee CRUD + RFID scan + break endpoints.

- GET operations require any authenticated user.
- POST / PUT / DELETE operations require admin role.
- POST /scan is open to any authenticated user (kiosk role included).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_active_user, get_db, require_admin
from app.core.config import settings
from app.models.attendance_settings import AttendanceSettings
from app.models.employee import Attendance, Employee
from app.models.user import User
from app.schemas.attendance import (
    BreakRequest,
    BreakResponse,
    DeleteResponse,
    EmployeeCreate,
    EmployeeRead,
    EmployeeUpdate,
    ScanRequest,
    ScanResponse,
)

router = APIRouter(tags=["employees"])
logger = logging.getLogger(__name__)


def _compute_today_hours(events: list[Attendance]) -> float:
    """Calculate accumulated work hours from today's IN/OUT pairs."""
    total_seconds = 0.0
    last_in_time = None
    # Process oldest first
    for ev in sorted(events, key=lambda e: e.timestamp):
        ts = ev.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ev.event_type == "IN":
            last_in_time = ts
        elif ev.event_type == "OUT" and last_in_time is not None:
            total_seconds += (ts - last_in_time).total_seconds()
            last_in_time = None
    # If currently clocked in, count up to now
    if last_in_time is not None:
        total_seconds += (datetime.now(timezone.utc) - last_in_time).total_seconds()
    return round(total_seconds / 3600, 2)


def _check_is_late(
    events: list[Attendance], work_start: str, grace_minutes: int, tz_offset: str
) -> bool:
    """Check if the employee's first IN today was after work_start + grace."""
    in_events = [e for e in events if e.event_type == "IN"]
    if not in_events:
        return False
    first_in = sorted(in_events, key=lambda e: e.timestamp)[0]
    ts = first_in.timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    # Parse timezone offset to convert UTC to local
    sign = 1 if tz_offset[0] == "+" else -1
    offset_parts = tz_offset[1:].split(":")
    offset_hours = int(offset_parts[0])
    offset_mins = int(offset_parts[1]) if len(offset_parts) > 1 else 0
    local_offset = timedelta(hours=sign * offset_hours, minutes=sign * offset_mins)
    local_tz = timezone(local_offset)
    local_time = ts.astimezone(local_tz)

    # Parse work_start (HH:MM)
    start_parts = work_start.split(":")
    start_hour, start_min = int(start_parts[0]), int(start_parts[1])
    cutoff = local_time.replace(
        hour=start_hour, minute=start_min, second=0, microsecond=0
    ) + timedelta(minutes=grace_minutes)

    return local_time > cutoff


# ── RFID Scan (PUBLIC — kiosk does not require login) ───────────────
@router.post("/scan", response_model=ScanResponse)
async def scan_card(
    body: ScanRequest,
    db: AsyncSession = Depends(get_db),
) -> ScanResponse:
    """Record an RFID card tap — toggles between IN and OUT.

    Uses WRITE LOCKING (with_for_update) to prevent race conditions (double tap).
    Returns enriched response with today's hours, last event, and late status.
    """
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Find or auto-register employee
    result = await db.execute(select(Employee).where(Employee.rfid_uid == body.uid))
    employee = result.scalar_one_or_none()

    if employee is None:
        try:
            employee = Employee(
                name=f"Employee-{body.uid[:8]}",
                rfid_uid=body.uid,
                department="Unassigned",
            )
            db.add(employee)
            await db.commit()
            await db.refresh(employee)
            logger.info("Auto-registered employee %s (UID %s)", employee.name, body.uid)
        except IntegrityError:
            await db.rollback()
            result = await db.execute(select(Employee).where(Employee.rfid_uid == body.uid))
            employee = result.scalar_one()
            logger.info("Race condition handled for UID %s", body.uid)

    if not employee.is_active:
        raise HTTPException(status_code=403, detail="Employee account is deactivated")

    # Lock last event to prevent race conditions
    last_result = await db.execute(
        select(Attendance)
        .where(Attendance.employee_id == employee.id, Attendance.date == today_str)
        .order_by(Attendance.timestamp.desc())
        .limit(1)
        .with_for_update()
    )
    last_event = last_result.scalar_one_or_none()
    event_type = "OUT" if last_event and last_event.event_type == "IN" else "IN"

    # Anti-bounce check
    if last_event:
        last_ts = last_event.timestamp
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)

        if (datetime.now(timezone.utc) - last_ts).total_seconds() < settings.BOUNCE_WINDOW_SECONDS:
            return ScanResponse(
                success=True,
                event=last_event.event_type,
                uid=body.uid,
                name=employee.name,
                attendance_id=last_event.id,
                attendance_timestamp=last_event.timestamp.isoformat(),
            )

    now = datetime.now(timezone.utc)
    attendance = Attendance(
        employee_id=employee.id,
        rfid_uid=body.uid,
        event_type=event_type,
        timestamp=now,
        date=today_str,
    )
    db.add(attendance)
    await db.commit()
    await db.refresh(attendance)

    logger.info("Scan %s for %s (UID %s)", event_type, employee.name, body.uid)

    # ── Compute enriched data ─────────────────────────────────────
    # Fetch all of today's events for this employee (including the one just created)
    all_today_result = await db.execute(
        select(Attendance)
        .where(Attendance.employee_id == employee.id, Attendance.date == today_str)
        .order_by(Attendance.timestamp.asc())
    )
    all_today = list(all_today_result.scalars().all())

    today_hours = _compute_today_hours(all_today)

    # Last event info (the event *before* this one)
    last_event_type = last_event.event_type if last_event else None
    last_event_time = last_event.timestamp.isoformat() if last_event else None

    # Late check — read attendance settings
    is_late = False
    try:
        settings_result = await db.execute(select(AttendanceSettings).limit(1))
        att_settings = settings_result.scalar_one_or_none()
        if att_settings:
            is_late = _check_is_late(
                all_today,
                att_settings.work_start,
                att_settings.grace_minutes,
                att_settings.timezone_offset,
            )
    except Exception as e:
        logger.warning("Could not check late status: %s", e)

    return ScanResponse(
        success=True,
        event=event_type,
        uid=body.uid,
        name=employee.name,
        attendance_id=attendance.id,
        attendance_timestamp=now.isoformat(),
        today_hours=today_hours,
        last_event_type=last_event_type,
        last_event_time=last_event_time,
        is_late=is_late,
    )


# ── Break endpoints ─────────────────────────────────────────────────
async def _record_break_event(uid: str, event_type: str, db: AsyncSession) -> BreakResponse:
    """Internal helper to record BREAK_START or BREAK_END events."""
    result = await db.execute(select(Employee).where(Employee.rfid_uid == uid))
    employee = result.scalar_one_or_none()
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    now = datetime.now(timezone.utc)
    attendance = Attendance(
        employee_id=employee.id,
        rfid_uid=uid,
        event_type=event_type,
        timestamp=now,
        date=now.strftime("%Y-%m-%d"),
    )
    db.add(attendance)
    await db.commit()
    await db.refresh(attendance)

    return BreakResponse(
        success=True,
        event=event_type,
        uid=uid,
        name=employee.name,
        attendance_id=attendance.id,
    )


@router.post("/break/start", response_model=BreakResponse)
async def break_start(
    body: BreakRequest,
    db: AsyncSession = Depends(get_db),
) -> BreakResponse:
    """Record a break start event for an employee."""
    return await _record_break_event(body.uid, "BREAK_START", db)


@router.post("/break/end", response_model=BreakResponse)
async def break_end(
    body: BreakRequest,
    db: AsyncSession = Depends(get_db),
) -> BreakResponse:
    """Record a break end event for an employee."""
    return await _record_break_event(body.uid, "BREAK_END", db)


# ── Employee CRUD ───────────────────────────────────────────────────
@router.get("/employees", response_model=list[EmployeeRead])
async def list_employees(
    skip: int = 0,
    limit: int = Query(default=50, le=500),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
) -> list[Employee]:
    query = (
        select(Employee)
        .where(Employee.is_active.is_(True))
        .order_by(Employee.name)
        .offset(skip)
        .limit(limit)
    )
    if search:
        # Escape SQL LIKE metacharacters to prevent wildcard injection
        safe_search = search.replace("%", r"\%").replace("_", r"\_")
        query = query.where(Employee.name.ilike(f"%{safe_search}%", escape="\\"))
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/employees", response_model=EmployeeRead, status_code=201)
async def create_employee(
    body: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Employee:
    existing = await db.execute(select(Employee).where(Employee.rfid_uid == body.rfid_uid))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"RFID UID '{body.rfid_uid}' already registered",
        )

    employee = Employee(**body.model_dump())
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    logger.info("Created employee %s (UID %s)", employee.name, employee.rfid_uid)
    return employee


@router.get("/employees/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
) -> Employee:
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id, Employee.is_active.is_(True))
    )
    emp = result.scalar_one_or_none()
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


@router.put("/employees/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    employee_id: int,
    body: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Employee:
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    emp = result.scalar_one_or_none()
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(emp, field, value)

    await db.commit()
    await db.refresh(emp)
    logger.info("Updated employee %d", employee_id)
    return emp


@router.delete("/employees/{employee_id}", response_model=DeleteResponse)
async def delete_employee(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> DeleteResponse:
    """Soft-delete (deactivate) an employee. Attendance history is preserved."""
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    emp = result.scalar_one_or_none()
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    emp.is_active = False
    await db.commit()
    logger.info("Soft-deleted employee %d (%s)", employee_id, emp.name)
    return DeleteResponse(success=True, message=f"Employee '{emp.name}' deactivated")
