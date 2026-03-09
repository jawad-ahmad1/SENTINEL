"""Timezone and date helpers shared across attendance endpoints."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

_TZ_OFFSET_RE = re.compile(r"^[+-](?:0\d|1\d|2[0-3]):[0-5]\d$")


class InvalidTimezoneOffset(ValueError):
    """Raised when a timezone offset does not match ±HH:MM."""


def parse_timezone_offset(offset: str) -> timezone:
    if not _TZ_OFFSET_RE.match(offset):
        raise InvalidTimezoneOffset(f"Invalid timezone offset: {offset}")

    sign = 1 if offset[0] == "+" else -1
    hours, minutes = offset[1:].split(":")
    delta = timedelta(hours=sign * int(hours), minutes=sign * int(minutes))
    return timezone(delta)


def ensure_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def local_now(offset: str) -> datetime:
    return utc_now().astimezone(parse_timezone_offset(offset))


def business_date_str(offset: str, base_utc: datetime | None = None) -> str:
    base = ensure_utc(base_utc)
    local = base.astimezone(parse_timezone_offset(offset))
    return local.date().isoformat()


def parse_iso_date(value: str) -> date:
    """Parse and validate YYYY-MM-DD strings."""
    return date.fromisoformat(value)


def is_late_arrival(
    scan_timestamp: datetime,
    work_start: str,
    grace_minutes: int,
    timezone_offset: str,
) -> bool:
    """Return True when first IN is after work_start + grace in local timezone."""
    scan_local = ensure_utc(scan_timestamp).astimezone(
        parse_timezone_offset(timezone_offset)
    )
    hour_str, minute_str = work_start.split(":")
    cutoff = scan_local.replace(
        hour=int(hour_str),
        minute=int(minute_str),
        second=0,
        microsecond=0,
    ) + timedelta(minutes=grace_minutes)
    return scan_local > cutoff
