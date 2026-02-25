"""
Auth endpoints — login (OAuth2 password flow) & token refresh.
"""

from __future__ import annotations

from fastapi import (APIRouter, Cookie, Depends, HTTPException, Request,
                     Response, status)
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Rate limiter — keyed by client IP
limiter = Limiter(key_func=get_remote_address)

from app.api.v1.deps import get_current_active_user, get_db, require_admin
from app.core.config import settings
from app.core.security import (create_access_token, create_refresh_token,
                               decode_refresh_token, get_password_hash,
                               verify_password)
from app.models.user import User
from app.schemas.attendance import LogoutResponse
from app.schemas.token import RefreshRequest, Token
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login_for_access_token(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Authenticate with user/pass. Returns 200 OK with HttpOnly Cookies."""
    result = await db.execute(
        select(User).where(User.email == form_data.username.lower().strip())
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # Set HttpOnly Cookies
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=settings.COOKIE_SECURE,  # Set to True in HTTPS production
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=Token)
@limiter.limit("10/minute")
async def refresh_access_token_endpoint(
    response: Response,
    request: Request,
    body: RefreshRequest | None = None,
    refresh_token_cookie: str | None = Cookie(None, alias="refresh_token"),
    db: AsyncSession = Depends(get_db),
) -> Token:
    # Priority: Body > Cookie
    token_str = None
    if body and body.refresh_token:
        token_str = body.refresh_token
    elif refresh_token_cookie:
        token_str = refresh_token_cookie

    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    payload = decode_refresh_token(token_str)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    new_access = create_access_token(user.id)
    new_refresh = create_refresh_token(user.id)

    response.set_cookie(
        key="access_token",
        value=f"Bearer {new_access}",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return Token(
        access_token=new_access,
        refresh_token=new_refresh,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response) -> LogoutResponse:
    """Clear auth cookies and end the session."""
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return LogoutResponse(message="Logged out")


# ── User management (admin-only) ───────────────────────────────────
@router.post("/users", response_model=UserRead, status_code=201)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> User:
    """Create a new user account (admin only)."""
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=get_password_hash(body.password),
        full_name=body.full_name,
        role=body.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Return profile of the currently authenticated user."""
    return current_user
