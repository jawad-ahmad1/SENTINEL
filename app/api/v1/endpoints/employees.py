"""
Employee CRUD + RFID scan + break endpoints.

- GET operations require any authenticated user.
- POST / PUT / DELETE operations require admin role.
- POST /scan is open to any authenticated user (kiosk role included).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.api.v1.deps import get_current_active_user, get_db, require_admin
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


# ── RFID Scan (PUBLIC — kiosk does not require login) ───────────────
@router.post("/scan", response_model=ScanResponse)
async def scan_card(
    body: ScanRequest,
    db: AsyncSession = Depends(get_db),
) -> ScanResponse:
    """Record an RFID card tap — toggles between IN and OUT.
    
    Uses WRITE LOCKING (with_for_update) to prevent race conditions (double tap).
    """
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Start transaction implicitly managed by FastAPI dependency, but we want explicit locking logic
    # Find or auto-register employee
    result = await db.execute(
        select(Employee).where(Employee.rfid_uid == body.uid)
    )
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
            # Race condition hit: another request created it just now.
            # Re-fetch the employee.
            result = await db.execute(
                select(Employee).where(Employee.rfid_uid == body.uid)
            )
            employee = result.scalar_one()
            logger.info("Race condition handled for UID %s", body.uid)

    if not employee.is_active:
        raise HTTPException(status_code=403, detail="Employee account is deactivated")

    # CRITICAL FIX: Lock the last attendance record to prevent race conditions
    # We lock the rows for this employee for this day to serialize duplicate requests
    # Note: with_for_update() requires a transaction.
    
    last_result = await db.execute(
        select(Attendance)
        .where(Attendance.employee_id == employee.id, Attendance.date == today_str)
        .order_by(Attendance.timestamp.desc())
        .limit(1)
        .with_for_update()  # <--- LOCKS ROW until commit
    )
    last_event = last_result.scalar_one_or_none()
    event_type = "OUT" if last_event and last_event.event_type == "IN" else "IN"

    # Anti-bounce check: If last event was < 5 seconds ago, ignore it? 
    # Optional but good practice. For now, the lock prevents simultaneous writes.
    # If the second request gets the lock after the first commits, it will see the NEW state 
    # and toggle back (IN -> OUT -> IN).
    # To strictly prevent "double tap" (IN..IN), we can check timestamp.
    
    if last_event:
        last_ts = last_event.timestamp
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)
        
        if (datetime.now(timezone.utc) - last_ts).total_seconds() < settings.BOUNCE_WINDOW_SECONDS:
            # It's a "bounce" or double tap. Return the existing state instead of creating new one.
            # This is better UX than toggling twice instantly.
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

    return ScanResponse(
        success=True,
        event=event_type,
        uid=body.uid,
        name=employee.name,
        attendance_id=attendance.id,
        attendance_timestamp=now.isoformat(),
    )


# ── Break endpoints ─────────────────────────────────────────────────
async def _record_break_event(
    uid: str, event_type: str, db: AsyncSession
) -> BreakResponse:
    """Internal helper to record BREAK_START or BREAK_END events."""
    result = await db.execute(
        select(Employee).where(Employee.rfid_uid == uid)
    )
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
        query = query.where(Employee.name.ilike(f"%{search}%"))
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/employees", response_model=EmployeeRead, status_code=201)
async def create_employee(
    body: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Employee:
    existing = await db.execute(
        select(Employee).where(Employee.rfid_uid == body.rfid_uid)
    )
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
        select(Employee).where(
            Employee.id == employee_id, Employee.is_active.is_(True)
        )
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
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
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
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    emp = result.scalar_one_or_none()
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    emp.is_active = False
    await db.commit()
    logger.info("Soft-deleted employee %d (%s)", employee_id, emp.name)
    return DeleteResponse(success=True, message=f"Employee '{emp.name}' deactivated")
