"""Tests for employee CRUD endpoints."""

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_employee(async_client: AsyncClient):
    """POST /employees should create a new employee."""
    resp = await async_client.post("/api/v1/employees", json={
        "name": "Bob Jones",
        "rfid_uid": "BOB-001",
        "email": "bob@example.com",
        "department": "Engineering",
        "position": "Developer",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Bob Jones"
    assert data["rfid_uid"] == "BOB-001"
    assert data["is_active"] is True
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_create_duplicate_rfid_rejected(async_client: AsyncClient):
    """Creating two employees with the same RFID should fail."""
    await async_client.post("/api/v1/employees", json={"name": "Emp1", "rfid_uid": "DUP-001"})
    resp = await async_client.post("/api/v1/employees", json={"name": "Emp2", "rfid_uid": "DUP-001"})
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_list_employees(async_client: AsyncClient):
    """GET /employees should return all active employees."""
    await async_client.post("/api/v1/employees", json={"name": "E1", "rfid_uid": "LIST-001"})
    await async_client.post("/api/v1/employees", json={"name": "E2", "rfid_uid": "LIST-002"})
    resp = await async_client.get("/api/v1/employees")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_list_employees_pagination(async_client: AsyncClient):
    """GET /employees with skip/limit should paginate."""
    for i in range(5):
        await async_client.post("/api/v1/employees", json={"name": f"P{i}", "rfid_uid": f"PAGE-{i:03d}"})
    resp = await async_client.get("/api/v1/employees?skip=2&limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_employee_by_id(async_client: AsyncClient):
    """GET /employees/{id} should return one employee."""
    create = await async_client.post("/api/v1/employees", json={"name": "Solo", "rfid_uid": "SOLO-001"})
    eid = create.json()["id"]
    resp = await async_client.get(f"/api/v1/employees/{eid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Solo"


@pytest.mark.asyncio
async def test_get_employee_not_found(async_client: AsyncClient):
    """Requesting a non-existent employee should return 404."""
    resp = await async_client.get("/api/v1/employees/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_employee(async_client: AsyncClient):
    """PUT /employees/{id} should update employee details."""
    create = await async_client.post("/api/v1/employees", json={"name": "Old Name", "rfid_uid": "UPD-001"})
    eid = create.json()["id"]
    resp = await async_client.put(f"/api/v1/employees/{eid}", json={"name": "New Name", "department": "Sales"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["department"] == "Sales"


@pytest.mark.asyncio
async def test_delete_employee_soft(async_client: AsyncClient):
    """DELETE /employees/{id} should soft-delete (deactivate)."""
    create = await async_client.post("/api/v1/employees", json={"name": "Del Me", "rfid_uid": "DEL-001"})
    eid = create.json()["id"]
    resp = await async_client.delete(f"/api/v1/employees/{eid}")
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Should no longer appear in active list
    listed = await async_client.get("/api/v1/employees")
    uids = [e["rfid_uid"] for e in listed.json()]
    assert "DEL-001" not in uids
