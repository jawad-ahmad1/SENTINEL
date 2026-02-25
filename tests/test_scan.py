"""Tests for the /scan endpoint."""

import pytest
from httpx import AsyncClient


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
    resp = await async_client.post(
        "/api/v1/scan", json={"uid": "<script>alert(1)</script>"}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_scan_rejects_too_long_uid(async_client: AsyncClient):
    """UID longer than 64 characters should be rejected."""
    long_uid = "A" * 65
    resp = await async_client.post("/api/v1/scan", json={"uid": long_uid})
    assert resp.status_code == 422
