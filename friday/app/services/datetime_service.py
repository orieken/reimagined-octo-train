
from datetime import datetime, timezone
import logging
from typing import Optional, Any, Dict, Union

logger = logging.getLogger(__name__)

def now_utc() -> datetime:
    """Return the current datetime in UTC."""
    return datetime.now(timezone.utc)

def parse_iso_datetime_to_utc(ts: Optional[Union[str, datetime]]) -> datetime:
    """
    Parse a timestamp string or datetime to timezone-aware UTC datetime.
    Falls back to Unix epoch on failure.
    """
    try:
        if isinstance(ts, datetime):
            return ts.astimezone(timezone.utc) if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        if isinstance(ts, str) and ts:
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
        raise ValueError("Missing or invalid timestamp")
    except Exception as e:
        logger.warning(f"Failed to parse timestamp '{ts}' to UTC: {e}")
        return default_epoch()

def isoformat_utc(dt: Optional[datetime]) -> str:
    """
    Convert a datetime to an ISO 8601 string in UTC.
    Returns an empty string if dt is None.
    """
    if dt is None:
        return ""
    return dt.astimezone(timezone.utc).isoformat()

def ensure_utc_datetime(value: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure a datetime is timezone-aware and in UTC.
    """
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

def is_aware(value: datetime) -> bool:
    """
    Check if a datetime is timezone-aware.
    """
    return value.tzinfo is not None and value.utcoffset() is not None

def ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime object is timezone-aware in UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def duration_in_milliseconds(start: Optional[datetime], end: Optional[datetime]) -> Optional[float]:
    """
    Calculate the duration between two datetimes in milliseconds.
    Returns None if either datetime is None.
    """
    if not start or not end:
        return None

    start = ensure_utc(start)
    end = ensure_utc(end)

    delta = end - start
    return delta.total_seconds() * 1000

def now_iso_utc() -> str:
    """Returns current UTC time as ISO string."""
    return isoformat_utc(now_utc())

def default_epoch() -> datetime:
    """Return a safe fallback datetime in UTC (Unix epoch)."""
    return datetime(1970, 1, 1, 0, 0).astimezone(timezone.utc)

def safe_utc_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return default_epoch()
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def to_utc_string(dt_obj: Optional[datetime]) -> str:
    return dt_obj.isoformat() if dt_obj else ""

def make_timestamps() -> Dict[str, datetime]:
    """Generate consistent UTC timestamps."""
    now = now_utc()
    return {"created_at": now, "updated_at": now}

def safe_duration(value: Any) -> float:
    """Convert duration to float safely, defaulting to 0.0."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0
