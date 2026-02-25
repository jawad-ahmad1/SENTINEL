"""Tests for reporting and analytics endpoints."""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


def _utc_today() -> str:
    """Return today's date in UTC, matching what scan_card stores."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


async def _seed_employee_with_scans(async_client: AsyncClient, uid="RPT-001", name="Reporter"):
    """Helper: register an employee and create IN/OUT scan pair for today."""
    await async_client.post("/api/v1/employees", json={"name": name, "rfid_uid": uid})
    from unittest.mock import patch

    from app.core.config import settings

    # Bypass bounce protection
    with patch.object(settings, "BOUNCE_WINDOW_SECONDS", 0.0):
        await async_client.post("/api/v1/scan", json={"uid": uid})  # IN
        await async_client.post("/api/v1/scan", json={"uid": uid})  # OUT
    return uid


@pytest.mark.asyncio
async def test_attendance_today(async_client: AsyncClient):
    """GET /attendance/today should return today's records."""
    await _seed_employee_with_scans(async_client)
    resp = await async_client.get("/api/v1/attendance/today")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # at least IN + OUT


@pytest.mark.asyncio
async def test_attendance_today_returns_name(async_client: AsyncClient):
    """Today's attendance should include the employee name."""
    await _seed_employee_with_scans(async_client, uid="NAME-01", name="NameTest")
    resp = await async_client.get("/api/v1/attendance/today")
    data = resp.json()
    names = [r.get("name") for r in data]
    assert "NameTest" in names


@pytest.mark.asyncio
async def test_reports_summary(async_client: AsyncClient):
    """GET /reports/summary/{date} should return daily summary."""
    await _seed_employee_with_scans(async_client)
    today = _utc_today()
    resp = await async_client.get(f"/api/v1/reports/summary/{today}")
    assert resp.status_code == 200
    data = resp.json()
    assert "details" in data
    assert len(data["details"]) >= 1


@pytest.mark.asyncio
async def test_reports_daily_csv(async_client: AsyncClient):
    """GET /reports/daily/csv should return CSV text."""
    await _seed_employee_with_scans(async_client)
    today = _utc_today()
    resp = await async_client.get(f"/api/v1/reports/daily/csv?date_str={today}")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "employee_id" in resp.text  # header row


@pytest.mark.asyncio
async def test_monthly_report(async_client: AsyncClient):
    """GET /reports/monthly/{year}/{month} should return monthly data."""
    await _seed_employee_with_scans(async_client)
    today_dt = datetime.now(timezone.utc)
    resp = await async_client.get(f"/api/v1/reports/monthly/{today_dt.year}/{today_dt.month}")
    assert resp.status_code == 200
    data = resp.json()
    assert "employees" in data
    assert data["year"] == today_dt.year
    assert data["month"] == today_dt.month


@pytest.mark.asyncio
async def test_analytics_trends(async_client: AsyncClient):
    """GET /analytics/trends should return date-grouped counts."""
    await _seed_employee_with_scans(async_client)
    resp = await async_client.get("/api/v1/analytics/trends")
    assert resp.status_code == 200
    data = resp.json()
    assert "trends" in data
    assert isinstance(data["trends"], list)


@pytest.mark.asyncio
async def test_employee_analytics(async_client: AsyncClient):
    """GET /analytics/employee/{id} should return 30-day analytics."""
    await async_client.post("/api/v1/employees", json={"name": "Analyst", "rfid_uid": "ANA-001"})
    await async_client.post("/api/v1/scan", json={"uid": "ANA-001"})  # IN
    # Get employee ID
    emps = (await async_client.get("/api/v1/employees")).json()
    emp = next(e for e in emps if e["rfid_uid"] == "ANA-001")
    resp = await async_client.get(f"/api/v1/analytics/employee/{emp['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Analyst"
    assert "daily_summary" in data


@pytest.mark.asyncio
async def test_employee_analytics_not_found(async_client: AsyncClient):
    """Analytics for non-existent employee should return 404."""
    resp = await async_client.get("/api/v1/analytics/employee/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    """GET /health should return ok."""
    resp = await async_client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "db" in data
    assert "redis" in data


@pytest.mark.asyncio
async def test_status_endpoint(async_client: AsyncClient):
    """GET /status should return employee and scan counts."""
    resp = await async_client.get("/api/v1/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_employees" in data
    assert "today_scans" in data
