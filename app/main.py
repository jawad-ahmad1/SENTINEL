"""
Sentinel v2.0 — Application entry point.

This is the **only** file that assembles the app.  All business logic
lives in the `api/`, `models/`, and `core/` packages.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import async_session_factory, engine

# Ensure all models are imported so metadata.create_all can see them
from app.models.absence_override import AbsenceOverride  # noqa: F401
from app.models.attendance_settings import AttendanceSettings  # noqa: F401
from app.models.employee import Attendance, Employee  # noqa: F401
from app.models.user import User

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialised")

    # Seed default admin user on first run
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.email == settings.FIRST_ADMIN_EMAIL)
        )
        if result.scalar_one_or_none() is None:
            admin = User(
                email=settings.FIRST_ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.FIRST_ADMIN_PASSWORD),
                full_name="System Administrator",
                role="admin",
            )
            session.add(admin)
            await session.commit()
            logger.info(
                "Default admin created: %s (password: <redacted>)",
                settings.FIRST_ADMIN_EMAIL,
            )

    logger.info("🚀 Sentinel v%s started", settings.VERSION)
    yield
    await engine.dispose()
    logger.info("Shutdown complete")


# ── App factory ─────────────────────────────────────────────────────
def create_app() -> FastAPI:
    application = FastAPI(
        title="Sentinel",
        description="Enterprise RFID Attendance System",
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handlers (prevent stack-trace leakage)
    register_exception_handlers(application)

    # Mount API v1
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Serve frontend static files (must be last — catch-all mount)
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    if frontend_dir.is_dir():
        application.mount(
            "/",
            StaticFiles(directory=str(frontend_dir), html=True),
            name="frontend",
        )
        logger.info("Frontend mounted from %s", frontend_dir)

    return application


app = create_app()
