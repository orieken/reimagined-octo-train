# app/services/datetime_service.py

from datetime import datetime, timezone
from typing import Optional


def now_utc() -> datetime:
    """Return the current datetime in UTC."""
    return datetime.now(timezone.utc)


def parse_iso_datetime_to_utc(ts: str) -> datetime:
    """
    Parse an ISO 8601 timestamp string to a timezone-aware datetime in UTC.
    If parsing fails, return a minimum datetime in UTC.
    """
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def isoformat_utc(dt: Optional[datetime]) -> str:
    """
    Convert a datetime to an ISO 8601 string in UTC.
    Returns an empty string if dt is None.
    """
    if not dt:
        return ""
    return dt.astimezone(timezone.utc).isoformat()

def parse_iso8601_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))