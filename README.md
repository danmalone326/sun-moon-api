# Sun-Moon API

An offline Python CGI implementation of the [Sunrise-Sunset.org v2 API](https://sunrise-sunset.org/api), using Skyfield and a locally installed JPL `de440s.bsp` ephemeris. It is intended for Apache 2 on Raspberry Pi and has no network dependency during requests. Sunrise-Sunset.org attribution is required when publishing data from this compatible service.

## Compatibility and extensions

`/sun-moon-api/v2` accepts `lat`, `lng`, `date`, `date_start`/`date_end`, `tz`, and `time_format=iso8601|unix`. It preserves the v2 single-day and range shapes, field names, local-time ISO values, Unix event timestamps, nullable events, twilight definitions, polar statuses, and error object `{error,message,docs}`. Date ranges are limited to 366 days. `time=HH:MM[:SS]` or an ISO timestamp adds `observer_position`; it is intentionally rejected for ranges. Each day also contains additive `lunar_position`, and `solar_position` includes the extra azimuth fields requested by this project.

### API extensions

The extensions are additive: existing Sunrise-Sunset.org-compatible fields are not removed or renamed.

- `time=HH:MM[:SS]` adds an instantaneous position query to a single-day request. A full ISO 8601 timestamp is also accepted, including `Z` or an explicit offset, for example `time=2026-08-01T06:15:00-07:00`. A time without an offset is interpreted in the selected or automatically detected local timezone.
- When `time` is supplied, the response includes `observer_position` with the evaluated local `time`, plus `sun` and `moon` objects. Both contain `azimuth` and geometric `elevation` in degrees. They also contain `apparent_elevation` with standard atmospheric refraction. The Moon additionally includes `distance_km` and instantaneous `illumination` as a percentage.
- Angular values are calculated at full precision and rounded to two displayed decimal places. Azimuths are degrees clockwise from true north, in the range 0 through less than 360. Distances are kilometers.
- Date-range requests containing `time` return HTTP 400 with an `invalid_time` error. This avoids implying one instantaneous time for multiple calendar days.
- `solar_position` adds `astronomical_dawn_azimuth`, `sunrise_azimuth`, `solar_noon_azimuth`, `solar_noon_altitude`, `sunset_azimuth`, and `astronomical_dusk_azimuth`. Azimuth values are degrees clockwise from true north; solar-noon altitude is degrees above the horizon.
- Each day adds `lunar_position` with `moonrise_azimuth` and `moonset_azimuth`. These values are degrees clockwise from true north and are `null` when the corresponding lunar event does not occur.

Example extended response fragment:

```json
{
  "observer_position": {
    "time": "2026-08-01T06:15:00-07:00",
    "sun": {"azimuth": 72.34, "elevation": 3.21, "apparent_elevation": 3.35},
    "moon": {"azimuth": 118.42, "elevation": 15.82, "apparent_elevation": 15.88, "distance_km": 384123.4, "illumination": 87.42}
  },
  "solar_position": {
    "astronomical_dawn_azimuth": 54.12,
    "sunrise_azimuth": 72.34,
    "solar_noon_azimuth": 180.01,
    "solar_noon_altitude": 52.77,
    "sunset_azimuth": 287.66,
    "astronomical_dusk_azimuth": 305.88
  },
  "lunar_position": {"moonrise_azimuth": 118.42, "moonset_azimuth": 241.58}
}
```

The supported compatibility floor is Python 3.7. On Python 3.7–3.9 the dependency file selects the older Skyfield/timezonefinder/NumPy stack; Python 3.7 is end-of-life, so upgrading the operating system remains strongly recommended.

The implementation uses Skyfield topocentric positions, standard USNO-style solar rise/set at -0.8333°, lunar upper-limb/refraction rise/set at -0.5667°, and Skyfield apparent positions for refraction. The public service may use different ephemeris revisions or operational rounding, so exact seconds can differ slightly. Timezone detection uses the maintained `timezonefinder` package and its bundled offline polygon database; explicit IANA zones use Python’s system tzdata. Coordinates where no polygon exists fall back to UTC.

## Setup and tests

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest
python -m compileall src cgi-bin
```

Install the ephemeris once, outside CGI:

```bash
.venv/bin/python scripts/download_ephemeris.py --output de440s.bsp
```

The script prints the SHA-256 digest and supports `--sha256 EXPECTED_DIGEST` for verification. Do not commit the resulting file. Production should install it at `/var/lib/sun-moon-api/de440s.bsp` (owned/readable by Apache), or set `SUN_MOON_EPHEMERIS` to another absolute path.

## Local CGI exercise

After downloading the ephemeris, run exactly:

```bash
QUERY_STRING='lat=36.72016&lng=-4.42034&date=2026-08-01&time=06:15:00' PATH_INFO=/v2 SUN_MOON_EPHEMERIS="$PWD/de440s.bsp" .venv/bin/python cgi-bin/v2
```

Example requests:

```text
/sun-moon-api/v2?lat=36.72016&lng=-4.42034
/sun-moon-api/v2?lat=40.7128&lng=-74.0060&date=2026-08-01&tz=America/Los_Angeles&time_format=unix
/sun-moon-api/v2?lat=36.72016&lng=-4.42034&date=2026-08-01&time=06:15:00
/sun-moon-api/v2?lat=36.72016&lng=-4.42034&date_start=2026-01-01&date_end=2026-01-31
```

## Apache on Raspberry Pi

```bash
sudo mkdir -p /var/www/sun-moon-api/cgi-bin /var/lib/sun-moon-api
sudo cp -a src /var/www/sun-moon-api/
sudo cp cgi-bin/v2 /var/www/sun-moon-api/cgi-bin/v2
sudo python3 -m venv /var/www/sun-moon-api/.venv
sudo /var/www/sun-moon-api/.venv/bin/pip install -r /path/to/sun-moon-api/requirements.txt
sudo /path/to/sun-moon-api/.venv/bin/python scripts/download_ephemeris.py --output /var/lib/sun-moon-api/de440s.bsp
sudo chown -R root:root /var/www/sun-moon-api /var/lib/sun-moon-api
sudo chmod 755 /var/www/sun-moon-api/cgi-bin/v2
sudo cp apache/sun-moon-api.conf /etc/apache2/conf-available/sun-moon-api.conf
sudo a2enmod cgi
sudo a2enconf sun-moon-api
sudo systemctl reload apache2
```

Apache does not inherit an activated shell environment. For this deployment, change the first line of `/var/www/sun-moon-api/cgi-bin/v2` to `#!/var/www/sun-moon-api/.venv/bin/python`, or use a small launcher that invokes that interpreter. The CGI wrapper must use the same virtualenv where Skyfield and the other dependencies were installed. Ensure the ephemeris is readable by the Apache user. A response is then available at `http://pi-address/sun-moon-api/v2?...`.

