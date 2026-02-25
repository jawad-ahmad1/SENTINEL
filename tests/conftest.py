"""
Shared test fixtures for the RFID Attendance System test suite.

Refactored for Async Support (aiosqlite + AsyncSession).
"""

import asyncio
import os
import sys
from typing import AsyncGenerator

import pytest

# Ensure project root is importable
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Override environment BEFORE importing application modules
# Use async sqlite driver
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
# CORS fix (JSON format)
os.environ["CORS_ORIGINS"] = '["*"]'

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.v1.deps import get_db
from app.db.base import Base
from app.db.session import (  # noqa: F401 — retained for engine patching if needed
    engine as app_engine,
)
from app.main import app

# Actually, since we set env var before import, app.db.session should pick it up.
# But app.db.session creates 'engine' at module level.
# We need to make sure we use a separate test engine and override the dependency.


# Create a test engine for the entire session
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# We need to run migrations or create tables.
# With async, we do this in an async fixture.


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_db():
    """Create all tables before usage and drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Return a httpx AsyncClient wired to the app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Return a raw database session for direct queries in tests."""
    async with TestingSessionLocal() as session:
        yield session


from app.api.v1.deps import get_current_active_user, require_admin

# ── Auth Overrides ──────────────────────────────────────────────────
from app.models.user import User


async def _override_get_current_active_user():
    return User(id=1, email="test@example.com", is_active=True, role="admin")


async def _override_require_admin():
    return User(id=1, email="admin@example.com", is_active=True, role="admin")


app.dependency_overrides[get_current_active_user] = _override_get_current_active_user
app.dependency_overrides[require_admin] = _override_require_admin
