from __future__ import annotations

from datetime import date
try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # Python 3.7 and 3.8
    from backports.zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from timezonefinder import TimezoneFinder

from .errors import APIError

_finder = TimezoneFinder()

def timezone_for_coordinates(lat: float, lng: float) -> str:
    name = _finder.timezone_at(lat=lat, lng=lng)
    # timezonefinder returns None over some water; UTC is the documented-safe fallback.
    return name or "UTC"

def get_timezone(name: str | None, lat: float, lng: float) -> ZoneInfo:
    selected = name or timezone_for_coordinates(lat, lng)
    try:
        return ZoneInfo(selected)
    except (ZoneInfoNotFoundError, ValueError):
        raise APIError("invalid_tz", f"Unknown tz '{selected}'. Use IANA identifiers like 'America/Los_Angeles'.")

def local_today(tz: ZoneInfo) -> date:
    from datetime import datetime
    return datetime.now(tz).date()

