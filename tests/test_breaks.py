"""Tests for break start/end endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_break_start_requires_registered_employee(async_client: AsyncClient):
    """Break start for an unknown UID should return 404."""
    resp = await async_client.post("/api/v1/break/start", json={"uid": "UNKNOWN-99"})
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_break_end_requires_registered_employee(async_client: AsyncClient):
    """Break end for an unknown UID should return 404."""
    resp = await async_client.post("/api/v1/break/end", json={"uid": "UNKNOWN-99"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_break_start_for_known_employee(async_client: AsyncClient):
    """Break start for a registered employee should succeed."""
    # Register employee first
    await async_client.post("/api/v1/employees", json={"name": "Breaker", "rfid_uid": "BRK-001"})
    resp = await async_client.post("/api/v1/break/start", json={"uid": "BRK-001"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["event"] == "BREAK_START"
    assert data["name"] == "Breaker"


@pytest.mark.asyncio
async def test_break_end_for_known_employee(async_client: AsyncClient):
    """Break end for a registered employee should succeed."""
    await async_client.post("/api/v1/employees", json={"name": "Ender", "rfid_uid": "BRK-002"})
    await async_client.post("/api/v1/break/start", json={"uid": "BRK-002"})
    resp = await async_client.post("/api/v1/break/end", json={"uid": "BRK-002"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["event"] == "BREAK_END"


@pytest.mark.asyncio
async def test_break_uid_validation(async_client: AsyncClient):
    """Break endpoints should validate UID format."""
    resp = await async_client.post("/api/v1/break/start", json={"uid": ""})
    assert resp.status_code == 422

    resp = await async_client.post("/api/v1/break/end", json={"uid": "!@#$%"})
    assert resp.status_code == 422
