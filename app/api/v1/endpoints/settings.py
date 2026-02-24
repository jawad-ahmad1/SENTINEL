"""
Settings CRUD endpoints — admin-configurable attendance rules.

Singleton pattern: only one row in attendance_settings. GET retrieves it,
PUT updates it. If no row exists, one is created with defaults on first GET.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_db, require_admin
from app.models.attendance_settings import AttendanceSettings
from app.models.user import User
from app.schemas.attendance import AttendanceSettingsRead, AttendanceSettingsUpdate

router = APIRouter(tags=["settings"])
logger = logging.getLogger(__name__)


async def _get_or_create_settings(db: AsyncSession) -> AttendanceSettings:
    """Fetch the singleton settings row, creating it with defaults if absent."""
    result = await db.execute(select(AttendanceSettings).limit(1))
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = AttendanceSettings(
            id=1,
            work_start="09:00",
            work_end="17:00",
            grace_minutes=15,
            timezone_offset="+05:00",
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        logger.info("Created default attendance settings")
    return settings


@router.get("/settings", response_model=AttendanceSettingsRead)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AttendanceSettings:
    """Get current attendance rules."""
    return await _get_or_create_settings(db)


@router.put("/settings", response_model=AttendanceSettingsRead)
async def update_settings(
    body: AttendanceSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AttendanceSettings:
    """Update attendance rules (work start, end, grace period, timezone)."""
    settings = await _get_or_create_settings(db)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)
    logger.info("Attendance settings updated: %s", body.model_dump(exclude_unset=True))
    return settings
