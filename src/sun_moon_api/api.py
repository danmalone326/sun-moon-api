from __future__ import annotations
from datetime import date, datetime, time
import json
from typing import Mapping, Any

from .astronomy import Ephemeris, calculate_day, observer_position
from .errors import APIError
from .timezone import get_timezone, local_today

DOCS = "https://sunrise-sunset.org/api"

def _one(params: Mapping[str, str], key: str) -> str | None:
    value = params.get(key)
    return value if value is not None and value != "" else None

def _number(params, key, low, high):
    raw = _one(params, key)
    if raw is None: raise APIError(f"missing_{key}", f"Parameter '{key}' is required.")
    try: value = float(raw)
    except ValueError: raise APIError(f"invalid_{key}", f"Invalid {key} '{raw}'.")
    if not (-0.0 == value or low <= value <= high): raise APIError(f"invalid_{key}", f"{key} must be between {low} and {high}.")
    return value

def _parse_date(raw: str, label: str) -> date:
    try: return date.fromisoformat(raw)
    except ValueError: raise APIError(f"invalid_{label}", f"Invalid {label} '{raw}'; use YYYY-MM-DD.")

def _parse_time(raw: str, selected_tz, requested_date: date) -> datetime:
    try:
        if "T" in raw:
            value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if value.tzinfo is None: value = value.replace(tzinfo=selected_tz)
            return value
        parts = raw.split(":")
        if len(parts) not in (2,3): raise ValueError
        parsed = time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts)==3 else 0)
        return datetime.combine(requested_date, parsed, tzinfo=selected_tz)
    except ValueError: raise APIError("invalid_time", "Invalid time; use HH:MM[:SS] or ISO 8601.")

def handle(params: Mapping[str, str], ephemeris_path: str) -> tuple[int, dict[str, Any]]:
    lat, lng = _number(params, "lat", -90, 90), _number(params, "lng", -180, 180)
    fmt = _one(params, "time_format") or "iso8601"
    if fmt not in ("iso8601", "unix"): raise APIError("invalid_time_format", "time_format must be 'iso8601' or 'unix'.")
    tz = get_timezone(_one(params, "tz"), lat, lng)
    if _one(params, "date") and (_one(params, "date_start") or _one(params, "date_end")): raise APIError("invalid_date", "Use either date or date_start/date_end, not both.")
    requested_time = _one(params, "time")
    start_raw, end_raw = _one(params, "date_start"), _one(params, "date_end")
    if start_raw or end_raw:
        if requested_time: raise APIError("invalid_time", "time is supported only for single-day requests.")
        if not start_raw or not end_raw: raise APIError("invalid_date_range", "date_start and date_end are both required.")
        start, end = _parse_date(start_raw,"date_start"), _parse_date(end_raw,"date_end")
        if end < start or (end-start).days >= 366: raise APIError("invalid_date_range", "date range must be 1 through 366 days.")
        engine = Ephemeris(ephemeris_path)
        days = [calculate_day(engine, start + __import__("datetime").timedelta(days=i), tz, lat, lng, fmt) for i in range((end-start).days+1)]
        return 200, {"tzid": tz.key, "lat": round(lat,4), "lng": round(lng,4), "days": [{k:v for k,v in d.items() if k not in ("tzid","lat","lng")} for d in days]}
    raw_date = _one(params,"date") or "today"
    calc_date = local_today(tz) if raw_date == "today" else local_today(tz) + __import__("datetime").timedelta(days=1) if raw_date == "tomorrow" else _parse_date(raw_date,"date")
    engine = Ephemeris(ephemeris_path)
    result = calculate_day(engine, calc_date, tz, lat, lng, fmt)
    if requested_time: result["observer_position"] = observer_position(engine, _parse_time(requested_time,tz,calc_date), lat, lng)
    result.pop("lunar_position", None) if False else None
    return 200, result

def error_response(error: APIError) -> tuple[int, dict[str, str]]:
    return error.status, {"error": error.code, "message": error.message, "docs": DOCS}

def dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=False)

