import pytest
import asyncio
from httpx import AsyncClient
import random
import string

# 💀 OMEGA FUZZER: GENERATING CHAOS

def generate_garbage(length=100):
    return "".join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*()", k=length))

def generate_sql_injection():
    payloads = ["' OR '1'='1", "'; DROP TABLE users--", "admin'--", "' UNION SELECT 1,2,3--"]
    return random.choice(payloads)

def generate_xss():
    payloads = ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "javascript:alert(1)"]
    return random.choice(payloads)

@pytest.mark.asyncio
async def test_omega_start_scan_fuzz(async_client: AsyncClient):
    """Fuzz the /scan endpoint with 100 random variations."""
    print("\n💀 FUZZING /scan with 100 iterations...")
    for i in range(100):
        uid = generate_garbage(random.randint(1, 255))
        # Mix in injections
        if i % 10 == 0: uid = generate_sql_injection()
        if i % 11 == 0: uid = generate_xss()
        
        resp = await async_client.post("/api/v1/scan", json={"uid": uid})
        # It should either work (create new user) or fail gracefully (400/422/403)
        # It should NEVER 500
        assert resp.status_code in [200, 400, 422, 403], f"CRITICAL: 500 Error on payload: {uid}"

@pytest.mark.asyncio
async def test_omega_auth_fuzz(async_client: AsyncClient):
    """Fuzz /auth/login with massive layouts."""
    print("\n💀 FUZZING /auth/login...")
    for i in range(50):
        email = generate_garbage(50) + "@test.com"
        password = generate_garbage(100)
        
        resp = await async_client.post(
            "/api/v1/auth/login", 
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert resp.status_code in [401, 400, 422], f"Login crashed with {email}"

@pytest.mark.asyncio
async def test_omega_reports_date_fuzz(async_client: AsyncClient):
    """Fuzz date parsing in reports."""
    dates = ["2020-01-01", "9999-12-31", "0000-00-00", "not-a-date", "' OR 1=1"]
    for d in dates:
        resp = await async_client.get(f"/api/v1/reports/summary/{d}")
        assert resp.status_code != 500, f"Reports crashed on date: {d}"
