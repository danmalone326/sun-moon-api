# Sun-Moon API

An offline Python CGI implementation of the [Sunrise-Sunset.org v2 API](https://sunrise-sunset.org/api), using Skyfield and a locally installed JPL `de440s.bsp` ephemeris. It is intended for Apache 2 on Raspberry Pi and has no network dependency during requests. Sunrise-Sunset.org attribution is required when publishing data from this compatible service.

## Compatibility and extensions

`/v2` accepts `lat`, `lng`, `date`, `date_start`/`date_end`, `tz`, and `time_format=iso8601|unix`. It preserves the v2 single-day and range shapes, field names, local-time ISO values, Unix event timestamps, nullable events, twilight definitions, polar statuses, and error object `{error,message,docs}`. Date ranges are limited to 366 days. `time=HH:MM[:SS]` or an ISO timestamp adds `observer_position`; it is intentionally rejected for ranges. Each day also contains additive `lunar_position`, and `solar_position` includes the extra azimuth fields requested by this project.

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
/v2?lat=36.72016&lng=-4.42034
/v2?lat=40.7128&lng=-74.0060&date=2026-08-01&tz=America/Los_Angeles&time_format=unix
/v2?lat=36.72016&lng=-4.42034&date=2026-08-01&time=06:15:00
/v2?lat=36.72016&lng=-4.42034&date_start=2026-01-01&date_end=2026-01-31
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

The CGI wrapper’s default shebang is suitable when Apache has a system Python with dependencies. For production virtualenv isolation, change the first line to `#!/var/www/sun-moon-api/.venv/bin/python`, or keep the wrapper as-is and use a launcher that executes that interpreter; Apache does not inherit an activated shell. Ensure the ephemeris is readable by the Apache user. A response is then available at `http://pi-address/v2?...`.

