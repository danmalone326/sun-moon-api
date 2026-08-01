from datetime import datetime, timezone
from typing import Any

def iso(value: datetime | None) -> str | None:
    return value.isoformat(timespec="seconds") if value else None

def event_value(value: datetime | None, fmt: str) -> str | int | None:
    if value is None:
        return None
    return int(value.astimezone(timezone.utc).timestamp()) if fmt == "unix" else iso(value)

def rounded(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(float(value), digits)

def pair(begin: datetime | None, end: datetime | None, fmt: str) -> dict[str, Any]:
    return {"begin": event_value(begin, fmt), "end": event_value(end, fmt)}

