"""Tests for the /scan endpoint."""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_settings import AttendanceSettings
from app.models.employee import Attendance


@pytest.mark.asyncio
async def test_scan_auto_registers_unknown_uid(async_client: AsyncClient):
    """Scanning an unknown UID should auto-register and clock IN."""
    resp = await async_client.post("/api/v1/scan", json={"uid": "TEST-0001"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["event"] == "IN"
    assert data["uid"] == "TEST-0001"
    assert data["name"].startswith("Employee")
    assert "attendance_id" in data
    assert "attendance_timestamp" in data


@pytest.mark.asyncio
async def test_scan_toggles_in_out(async_client: AsyncClient):
    """Consecutive scans should alternate between IN and OUT."""
    from unittest.mock import patch

    from app.core.config import settings

    with patch.object(settings, "BOUNCE_WINDOW_SECONDS", 0.0):
        # First scan → IN
        r1 = await async_client.post("/api/v1/scan", json={"uid": "TEST-0002"})
        assert r1.json()["event"] == "IN"

        # Second scan → OUT
        r2 = await async_client.post("/api/v1/scan", json={"uid": "TEST-0002"})
        assert r2.json()["event"] == "OUT"

        # Third scan → IN again
        r3 = await async_client.post("/api/v1/scan", json={"uid": "TEST-0002"})
        assert r3.json()["event"] == "IN"


@pytest.mark.asyncio
async def test_scan_returns_employee_name(async_client: AsyncClient):
    """After registering an employee, scan should return their name."""
    # Register named employee first
    await async_client.post(
        "/api/v1/employees", json={"name": "Alice Smith", "rfid_uid": "ALICE-01"}
    )
    resp = await async_client.post("/api/v1/scan", json={"uid": "ALICE-01"})
    data = resp.json()
    assert data["name"] == "Alice Smith"


@pytest.mark.asyncio
async def test_scan_rejects_empty_uid(async_client: AsyncClient):
    """Empty UID should be rejected with a 422 validation error."""
    resp = await async_client.post("/api/v1/scan", json={"uid": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_scan_rejects_invalid_uid(async_client: AsyncClient):
    """UID with special characters should be rejected."""
    resp = await async_client.post("/api/v1/scan", json={"uid": "<script>alert(1)</script>"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_scan_rejects_too_long_uid(async_client: AsyncClient):
    """UID longer than 64 characters should be rejected."""
    long_uid = "A" * 65
    resp = await async_client.post("/api/v1/scan", json={"uid": long_uid})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_scan_uses_business_timezone_for_attendance_date(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Stored attendance date should follow configured business timezone, not raw UTC date.
    """
    settings_row = AttendanceSettings(
        id=1,
        work_start="09:00",
        work_end="17:00",
        grace_minutes=15,
        timezone_offset="+05:00",
    )
    db_session.add(settings_row)
    await db_session.commit()

    from app.api.v1.endpoints import employees as employees_endpoint

    original_utc_now = employees_endpoint.utc_now
    employees_endpoint.utc_now = lambda: datetime(2026, 1, 1, 22, 30, tzinfo=timezone.utc)
    try:
        resp = await async_client.post("/api/v1/scan", json={"uid": "TZ-EDGE-01"})
        assert resp.status_code == 200
    finally:
        employees_endpoint.utc_now = original_utc_now

    result = await db_session.execute(
        select(Attendance).where(Attendance.rfid_uid == "TZ-EDGE-01")
    )
    row = result.scalar_one()
    assert row.date == "2026-01-02"
