from datetime import date, datetime, timezone
import json
import pytest
from sun_moon_api.api import _parse_date, _parse_time, error_response
from sun_moon_api.astronomy import _select_events
from sun_moon_api.errors import APIError
from sun_moon_api.timezone import get_timezone

def test_contract_sample_keys():
    sample = {"date":"2026-01-15","tzid":"Europe/Madrid","utc_offset":"+01:00","lat":36.7202,"lng":-4.4203,
      "sunrise":None,"sunset":None,"solar_noon":None,"day_length":35924,"sun_status":"normal",
      "civil_twilight_begin":None,"civil_twilight_end":None,"nautical_twilight_begin":None,"nautical_twilight_end":None,
      "astronomical_twilight_begin":None,"astronomical_twilight_end":None,"dawn":None,"dusk":None,"first_light":None,"last_light":None,
      "golden_hour":{"morning":{"begin":None,"end":None},"evening":{"begin":None,"end":None}},
      "blue_hour":{"morning":{"begin":None,"end":None},"evening":{"begin":None,"end":None}},
      "solar_position":{"sunrise_azimuth":118.31,"sunset_azimuth":241.82,"solar_noon_azimuth":180.09,"solar_noon_altitude":32.06},
      "moonrise":None,"moonset":None,"moon_phase":"Waning Crescent","moon_illumination":10.62}
    assert set(sample) >= {"date","tzid","utc_offset","lat","lng","solar_position","moon_phase","moon_illumination"}

@pytest.mark.parametrize("raw", ["abc", "2026/01/01", "2026-02-30"])
def test_bad_dates(raw):
    with pytest.raises(APIError): _parse_date(raw, "date")

def test_timezone_and_time_parsing():
    tz=get_timezone("America/Los_Angeles", 0, 0)
    assert tz.key == "America/Los_Angeles"
    assert _parse_time("06:15:30", tz, date(2026,8,1)).utcoffset().total_seconds() == -7*3600
    assert _parse_time("2026-08-01T13:15:00Z", tz, date(2026,8,1)).hour == 13

def test_invalid_timezone_error_shape():
    status, body=error_response(APIError("invalid_tz", "bad"))
    assert status == 400 and set(body) == {"error","message","docs"}



class FakeSkyfieldTime:
    def __init__(self, value):
        self.value = value

    def utc_datetime(self):
        return self.value

def test_events_from_adjacent_date_are_excluded():
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/Los_Angeles")
    requested = date(2026, 8, 6)
    times = [
        FakeSkyfieldTime(datetime(2026, 8, 6, 21, 36, tzinfo=timezone.utc)),
        FakeSkyfieldTime(datetime(2026, 8, 7, 7, 32, tzinfo=timezone.utc)),
    ]
    ok = [True, True]
    assert _select_events(times[1:], [True], requested, tz, True) is None
    assert _select_events(times, ok, requested, tz, False).value == times[0].value
