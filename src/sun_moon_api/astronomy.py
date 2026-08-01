from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from skyfield import almanac
from skyfield.api import load, wgs84
from skyfield.earthlib import refraction

from .formatting import event_value, pair, rounded

SOLAR_HORIZONS = {"sunrise": -0.8333333333, "civil": -6.0, "nautical": -12.0, "astronomical": -18.0}
MOON_HORIZON = -0.5666666667

class Ephemeris:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path.is_file():
            raise FileNotFoundError(f"Ephemeris not found: {self.path}. Run scripts/download_ephemeris.py")
        self.ts = load.timescale()
        self.eph = load(str(self.path))

def _time_window(calc_date: date, tz, ts):
    start = datetime.combine(calc_date, time.min, tzinfo=tz).astimezone(timezone.utc)
    end = start + timedelta(days=2)
    return ts.from_datetime(start), ts.from_datetime(end)

def _event(observer, body, t0, t1, rising: bool, horizon: float):
    fn = almanac.find_risings if rising else almanac.find_settings
    times, ok = fn(observer, body, t0, t1, horizon_degrees=horizon)
    selected = [times[i] for i, valid in enumerate(ok) if bool(valid)]
    return selected[0] if selected else None

def _dt(t, tz):
    return t.utc_datetime().astimezone(tz) if t is not None else None

def _azalt(observer, body, t):
    if t is None:
        return None, None
    apparent = observer.at(t).observe(body).apparent()
    alt, az, _ = apparent.altaz()
    return float(az.degrees) % 360.0, float(alt.degrees)

def calculate_day(engine: Ephemeris, calc_date: date, tz, lat: float, lng: float, time_format: str = "iso8601") -> dict[str, Any]:
    earth, sun, moon = engine.eph["earth"], engine.eph["sun"], engine.eph["moon"]
    topo = wgs84.latlon(lat, lng)
    observer = earth + topo
    t0, t1 = _time_window(calc_date, tz, engine.ts)
    events: dict[str, Any] = {}
    solar_times: dict[str, Any] = {}
    for key, horizon in SOLAR_HORIZONS.items():
        rising = _event(observer, sun, t0, t1, True, horizon)
        setting = _event(observer, sun, t0, t1, False, horizon)
        solar_times[key] = (rising, setting)
    sunrise, sunset = solar_times["sunrise"]
    civil_begin, civil_end = solar_times["civil"]
    nautical_begin, nautical_end = solar_times["nautical"]
    astro_begin, astro_end = solar_times["astronomical"]
    # find_transits returns meridian crossings; the first valid crossing in this window is noon.
    transit_times = almanac.find_transits(observer, sun, t0, t1)
    noon_t = transit_times[0] if len(transit_times) else None
    moonrise_t = _event(observer, moon, t0, t1, True, MOON_HORIZON)
    moonset_t = _event(observer, moon, t0, t1, False, MOON_HORIZON)
    local = lambda t: _dt(t, tz)
    noon = local(noon_t)
    sunrise_l, sunset_l = local(sunrise), local(sunset)
    day_length = int((sunset - sunrise) * 86400) if sunrise is not None and sunset is not None else None
    status = "normal"
    if sunrise is None and sunset is None:
        status = "polar_night" if (civil_begin is None and civil_end is None) else "normal"
    elif sunrise is None and sunset is not None:
        status = "polar_night"
    elif sunrise is not None and sunset is None:
        status = "midnight_sun" if day_length is None else "normal"
    if status == "midnight_sun" and sunrise is not None and sunset is None:
        day_length = 86400
    def ev(x): return event_value(local(x), time_format)
    sunrise_az, _ = _azalt(observer, sun, sunrise)
    sunset_az, _ = _azalt(observer, sun, sunset)
    noon_az, noon_alt = _azalt(observer, sun, noon_t)
    astro_dawn_az, _ = _azalt(observer, sun, astro_begin)
    astro_dusk_az, _ = _azalt(observer, sun, astro_end)
    moonrise_az, _ = _azalt(observer, moon, moonrise_t)
    moonset_az, _ = _azalt(observer, moon, moonset_t)
    def altitude_event(target, horizon, rising):
        return local(_event(observer, target, t0, t1, rising, horizon))
    golden_m_begin = altitude_event(sun, 6.0, True)  # overwritten by exact -4 crossing below
    # The golden/blue boundaries are ordered crossings of -6, -4, +6 in this day window.
    def crossings(horizon):
        a = _event(observer, sun, t0, t1, True, horizon)
        b = _event(observer, sun, t0, t1, False, horizon)
        return local(a), local(b)
    minus4_r, minus4_s = crossings(-4.0)
    plus6_r, plus6_s = crossings(6.0)
    blue_m, blue_e = pair(local(civil_begin), minus4_r, time_format), pair(minus4_s, local(civil_end), time_format)
    golden_m, golden_e = pair(minus4_r, plus6_r, time_format), pair(plus6_s, minus4_s, time_format)
    phase_angle = float(moon.at(noon_t if noon_t is not None else t0).observe(sun).apparent().separation_from(moon.at(noon_t if noon_t is not None else t0).observe(sun).apparent()).degrees) if False else float(almanac.moon_phase(engine.eph, noon_t if noon_t is not None else t0).degrees)
    names = [(22.5, "New Moon"), (67.5, "Waxing Crescent"), (112.5, "First Quarter"), (157.5, "Waxing Gibbous"), (202.5, "Full Moon"), (247.5, "Waning Gibbous"), (292.5, "Last Quarter"), (337.5, "Waning Crescent"), (360.1, "New Moon")]
    phase = next(name for limit, name in names if phase_angle < limit)
    illumination = (1 - __import__("math").cos(__import__("math").radians(phase_angle))) * 50
    return {"date": calc_date.isoformat(), "tzid": tz.key, "utc_offset": calc_date_offset(calc_date, tz), "lat": round(lat,4), "lng": round(lng,4),
      "sunrise": ev(sunrise), "sunset": ev(sunset), "solar_noon": ev(noon_t), "day_length": day_length, "sun_status": status,
      "civil_twilight_begin": ev(civil_begin), "civil_twilight_end": ev(civil_end), "nautical_twilight_begin": ev(nautical_begin), "nautical_twilight_end": ev(nautical_end),
      "astronomical_twilight_begin": ev(astro_begin), "astronomical_twilight_end": ev(astro_end), "dawn": ev(civil_begin), "dusk": ev(civil_end), "first_light": ev(astro_begin), "last_light": ev(astro_end),
      "golden_hour": {"morning": golden_m, "evening": golden_e}, "blue_hour": {"morning": blue_m, "evening": blue_e},
      "solar_position": {"astronomical_dawn_azimuth": rounded(astro_dawn_az), "sunrise_azimuth": rounded(sunrise_az), "solar_noon_azimuth": rounded(noon_az), "solar_noon_altitude": rounded(noon_alt), "sunset_azimuth": rounded(sunset_az), "astronomical_dusk_azimuth": rounded(astro_dusk_az)},
      "moonrise": ev(moonrise_t), "moonset": ev(moonset_t), "moon_phase": phase, "moon_illumination": rounded(illumination),
      "lunar_position": {"moonrise_azimuth": rounded(moonrise_az), "moonset_azimuth": rounded(moonset_az)}}

def calc_date_offset(d: date, tz) -> str:
    return datetime.combine(d, time.min, tzinfo=tz).strftime("%z")[:3] + ":" + datetime.combine(d, time.min, tzinfo=tz).strftime("%z")[3:]

def observer_position(engine: Ephemeris, when: datetime, lat: float, lng: float) -> dict[str, Any]:
    earth, sun, moon = engine.eph["earth"], engine.eph["sun"], engine.eph["moon"]
    observer = earth + wgs84.latlon(lat, lng)
    t = engine.ts.from_datetime(when.astimezone(timezone.utc))
    def pos(body, apparent=False):
        p = observer.at(t).observe(body).apparent()
        alt, az, distance = p.altaz(temperature_C=15.0, pressure_mbar=1010.0) if apparent else p.altaz()
        return rounded(float(az.degrees) % 360), rounded(float(alt.degrees)), distance.km
    saz, sel, _ = pos(sun, False); _, sap, _ = pos(sun, True)
    maz, mel, md = pos(moon, False); _, map_, _ = pos(moon, True)
    illumination = (1 - __import__("math").cos(__import__("math").radians(float(almanac.moon_phase(engine.eph, t).degrees)))) * 50
    return {"time": when.isoformat(timespec="seconds"), "sun": {"azimuth": saz, "elevation": sel, "apparent_elevation": sap}, "moon": {"azimuth": maz, "elevation": mel, "apparent_elevation": map_, "distance_km": rounded(md,1), "illumination": rounded(illumination)}}
