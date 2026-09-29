import datetime
from typing import Optional, Union

def utcnow() -> datetime.datetime:
    """
    Return a naive UTC datetime representing current time.
    Strictly adheres to SQLite naive UTC storage conventions.
    """
    return datetime.datetime.utcnow()

def to_iso_z(dt: Optional[datetime.datetime]) -> Optional[str]:
    """
    Format a naive UTC datetime as an ISO-8601 string with 'Z' suffix at API boundaries.
    """
    if dt is None:
        return None
    iso = dt.isoformat()
    if not iso.endswith("Z"):
        return f"{iso}Z"
    return iso

def parse_iso_utc(value: Union[str, datetime.datetime]) -> datetime.datetime:
    """
    Parse an ISO-8601 string or datetime into a naive UTC datetime for database storage.
    Eliminates aware/naive mixing.
    """
    if isinstance(value, datetime.datetime):
        if value.tzinfo is not None:
            return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return value

    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    
    parsed = datetime.datetime.fromisoformat(s)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return parsed
