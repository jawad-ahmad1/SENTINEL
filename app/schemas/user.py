"""Pydantic schemas for User CRUD."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

_VALID_ROLES = {"admin", "manager", "kiosk", "readonly"}


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str | None = None
    role: str = "readonly"

    @field_validator("role")
    @classmethod
    def _validate_role(cls, v: str) -> str:
        if v not in _VALID_ROLES:
            raise ValueError(f"Role must be one of: {_VALID_ROLES}")
        return v

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v:
            raise ValueError("Invalid email address")
        return v


class UserRead(BaseModel):
    id: int
    email: str
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime | None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None

    @field_validator("role")
    @classmethod
    def _validate_role(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_ROLES:
            raise ValueError(f"Role must be one of: {_VALID_ROLES}")
        return v
