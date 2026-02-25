"""
Async SQLAlchemy engine & session factory (asyncpg driver).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine_args = {
    "echo": False,
    "pool_pre_ping": True,
}

if "postgresql" in settings.DATABASE_URL:
    engine_args.update(
        {
            "pool_size": 20,
            "max_overflow": 10,
            "pool_recycle": 300,
        }
    )

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_args,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an AsyncSession and closes it after use."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
