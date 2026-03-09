"""Validation tests for attendance settings endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_settings_reject_invalid_time_format(async_client: AsyncClient):
    resp = await async_client.put(
        "/api/v1/settings",
        json={"work_start": "9:00"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_settings_reject_invalid_timezone_format(async_client: AsyncClient):
    resp = await async_client.put(
        "/api/v1/settings",
        json={"timezone_offset": "+5"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_settings_reject_non_sensical_work_window(async_client: AsyncClient):
    resp = await async_client.put(
        "/api/v1/settings",
        json={"work_start": "17:00", "work_end": "09:00"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_settings_accept_valid_updates(async_client: AsyncClient):
    resp = await async_client.put(
        "/api/v1/settings",
        json={
            "work_start": "09:00",
            "work_end": "18:00",
            "grace_minutes": 10,
            "allowed_absent": 3,
            "allowed_leave": 8,
            "allowed_half_day": 2,
            "timezone_offset": "+05:00",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["work_start"] == "09:00"
    assert data["work_end"] == "18:00"
    assert data["timezone_offset"] == "+05:00"
