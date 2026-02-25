"""
FastAPI dependencies — auth guards and database session.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import async_session_factory
from app.models.user import User

# We use auto_error=False so we can manually check for the cookie if header is missing
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# ── Database session ────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


# ── Auth dependencies ───────────────────────────────────────────────
async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    access_token: Optional[str] = Cookie(default=None),  # Read from HttpOnly Cookie
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode JWT from Header OR Cookie, look up user."""

    # Priority: Header > Cookie
    final_token = token
    if not final_token:
        # Try cookie (formatted as "Bearer <token>" or just "<token>")
        if access_token:
            # Our auth.py sets values as "Bearer <token>"
            if access_token.startswith("Bearer "):
                final_token = access_token.split(" ")[1]
            else:
                final_token = access_token

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not final_token:
        raise credentials_exc

    payload = decode_access_token(final_token)
    if payload is None:
        raise credentials_exc

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exc

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exc
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Reject inactive accounts."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Only allow admin role to proceed."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
