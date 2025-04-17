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

# Make sure parse_iso8601_utc always returns timezone-aware datetime
def parse_iso8601_utc(value: str) -> datetime:
    """Convert ISO 8601 string to timezone-aware datetime in UTC."""
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)

    # Handle 'Z' notation for UTC
    if value.endswith('Z'):
        value = value.replace('Z', '+00:00')

    # Parse and ensure it's timezone-aware
    dt = datetime.fromisoformat(value)

    # Add timezone if naive
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC if it has a different timezone
        dt = dt.astimezone(timezone.utc)

    return dt


def ensure_utc_datetime(timestamp) -> datetime:
    """
    Convert any timestamp representation to a UTC timezone-aware datetime.

    Args:
        timestamp: Can be string (ISO format), datetime (naive or aware), or None

    Returns:
        UTC timezone-aware datetime
    """
    if timestamp is None:
        return now_utc()

    if isinstance(timestamp, str):
        return parse_iso8601_utc(timestamp)

    if isinstance(timestamp, datetime):
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc)

    # Default fallback
    return now_utc()

