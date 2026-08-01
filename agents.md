# Sun-Moon API Development Instructions

## Project purpose

Build a small, read-only astronomy JSON API implemented as a Python CGI program for Apache 2 on a Raspberry Pi.

The API must be a drop-in replacement for the Sunrise-Sunset.org API v2 wherever practical. Existing clients should be able to switch from the public service to this implementation by changing only the base URL.

The API also extends the compatible response with instantaneous Sun and Moon azimuth/elevation information.

## Runtime and deployment constraints

* Target platform: Raspberry Pi OS with Apache 2.
* Deployment model: traditional Apache `cgi-bin`; no Flask, FastAPI, Uvicorn, persistent daemon, database, or container is required.
* Language: Python 3.
* Astronomy calculations: Skyfield using a locally stored JPL ephemeris.
* Prefer `de440s.bsp`.
* The production server may not have Internet access at request time.
* Never download ephemeris data during a CGI request.
* All HTTP responses must be valid JSON with an appropriate `Content-Type: application/json` header.
* CGI output must not contain debug text before or after the JSON document.
* Send diagnostics to stderr, not stdout.

## Python environment

Use a project-local Python virtual environment named `.venv`.

For local development:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

All development, testing, and validation commands must use the virtual environment.

Do not install project dependencies globally.

Add `.venv/` to `.gitignore`.

The CGI deployment documentation must explain both supported approaches:

1. Create a production virtual environment and configure the CGI script shebang to use that environment’s Python interpreter.
2. Use a small launcher script that invokes the virtual environment’s Python interpreter.

Do not assume Apache executes with the developer’s activated shell environment.

When working in this repository, Codex should:

* Create `.venv` if it does not exist.
* Install the required dependencies into `.venv`.
* Run tests using `.venv/bin/python`.
* Record all direct dependencies in `requirements.txt`.
* Report clearly if package installation is blocked by permissions or unavailable network access.

## Compatibility requirements

Implement the Sunrise-Sunset.org API v2 contract documented at:

https://sunrise-sunset.org/api

The compatible endpoint must be available as:

```text
/v2
```

Support these query parameters:

* `lat`: required decimal latitude, from -90 through 90.
* `lng`: required decimal longitude, from -180 through 180.
* `date`: optional `YYYY-MM-DD`, `today`, or `tomorrow`.
* `date_start`: optional range start in `YYYY-MM-DD`.
* `date_end`: optional range end in `YYYY-MM-DD`.
* `tz`: optional IANA timezone name.
* `time_format`: optional `iso8601` or `unix`.

Follow the upstream API’s documented behavior for:

* Defaults.
* Local-date interpretation.
* Automatic timezone detection from latitude and longitude.
* Single-day response shape.
* Date-range response shape.
* Field names and nesting.
* ISO 8601 formatting.
* Unix timestamps.
* Nullable events.
* Polar-day and polar-night behavior.
* Validation errors and HTTP status codes.

Preserve all documented v2 response fields, including:

* `date`
* `tzid`
* `utc_offset`
* `lat`
* `lng`
* `sunrise`
* `sunset`
* `solar_noon`
* `day_length`
* `sun_status`
* `civil_twilight_begin`
* `civil_twilight_end`
* `nautical_twilight_begin`
* `nautical_twilight_end`
* `astronomical_twilight_begin`
* `astronomical_twilight_end`
* `dawn`
* `dusk`
* `first_light`
* `last_light`
* `golden_hour`
* `blue_hour`
* `solar_position`
* `moonrise`
* `moonset`
* `moon_phase`
* `moon_illumination`

Compatibility fields must retain their documented meanings and units.

Do not knowingly invent upstream behavior. Document any unavoidable difference.

## API extensions

Add an optional query parameter:

```text
time=HH:MM[:SS]
```

Also accept a full ISO 8601 timestamp:

```text
time=YYYY-MM-DDTHH:MM[:SS][Z|±HH:MM]
```

Interpret a time without an offset in the selected or automatically detected local timezone.

When `time` is supplied for a single-day request, add this top-level object without removing or renaming any compatibility fields:

```json
{
  "observer_position": {
    "time": "2026-08-01T06:15:00-07:00",
    "sun": {
      "azimuth": 72.34,
      "elevation": 3.21,
      "apparent_elevation": 3.35
    },
    "moon": {
      "azimuth": 118.42,
      "elevation": 15.82,
      "apparent_elevation": 15.88,
      "distance_km": 384123.4,
      "illumination": 87.42
    }
  }
}
```

Definitions:

* Azimuth is degrees clockwise from true north in the range 0 through less than 360.
* Elevation is geometric topocentric elevation in degrees.
* Apparent elevation includes standard atmospheric refraction when Skyfield supports it appropriately.
* Moon illumination is a percentage from 0 through 100.
* Distances are kilometers.
* Round displayed angular values to a sensible precision without reducing calculation precision internally.

For date-range requests, initially reject `time` with a clear HTTP 400 JSON response unless a clean, well-tested interpretation is implemented and documented.

Add these values to the existing `solar_position` object:

* `astronomical_dawn_azimuth`
* `sunrise_azimuth`
* `solar_noon_azimuth`
* `solar_noon_altitude`
* `sunset_azimuth`
* `astronomical_dusk_azimuth`

Add this compatible extension object for each day:

```json
{
  "lunar_position": {
    "moonrise_azimuth": 73.21,
    "moonset_azimuth": 286.42
  }
}
```

Values must be `null` when the corresponding event does not occur.

Additional extension fields must be additive. Do not alter upstream-compatible fields merely to make extensions easier.

## Accuracy requirements

Use topocentric calculations for the supplied observer coordinates.

Account for:

* Observer latitude and longitude.
* Timezone and daylight-saving transitions.
* The standard solar rise/set definition used by the reference API.
* Atmospheric refraction where required by the event definition.
* The apparent angular radius or limb convention needed for rise/set compatibility.
* Moon parallax for lunar rise/set and position.
* Dates on which events do not occur.
* High-latitude and polar conditions.

Skyfield APIs should be used rather than handwritten orbital formulas.

Timezone lookup must operate locally. Choose a maintained Python package that can determine an IANA timezone from coordinates and document its offline data dependency.

## Project structure

Keep astronomy calculations independent from CGI transport logic.

A reasonable structure is:

```text
sun-moon-api/
├── AGENTS.md
├── README.md
├── requirements.txt
├── pyproject.toml
├── .gitignore
├── src/
│   └── sun_moon_api/
│       ├── __init__.py
│       ├── astronomy.py
│       ├── api.py
│       ├── errors.py
│       ├── formatting.py
│       └── timezone.py
├── cgi-bin/
│   └── v2
├── scripts/
│   └── download_ephemeris.py
└── tests/
```

The CGI file should be a thin executable wrapper. Business logic must remain importable and directly testable without Apache.

## Engineering requirements

* Use type hints.
* Keep functions focused and testable.
* Validate all external input.
* Do not pass user input to a shell.
* Do not expose stack traces to clients.
* Use deterministic JSON serialization.
* Use UTC internally where practical.
* Use timezone-aware datetimes only.
* Avoid global mutable request state.
* Cache immutable data only within a process; do not depend on CGI process persistence.
* Pin direct dependency versions to compatible ranges.
* Do not commit the large JPL ephemeris file to Git.
* Include an ephemeris checksum or a documented verification process.
* Include appropriate Apache deployment and file-permission instructions.
* Do not require root privileges to run tests.

## Testing requirements

Use `pytest`.

Tests must cover at least:

* Missing and malformed parameters.
* Latitude and longitude boundaries.
* Date parsing.
* `today` and `tomorrow` in the location’s timezone.
* Explicit timezone selection.
* Daylight-saving transitions.
* ISO 8601 and Unix output.
* Single-day and date-range response shapes.
* Range-length validation.
* Null events.
* Polar day and polar night.
* Sun and Moon azimuth/elevation.
* Moonrise and moonset azimuth.
* CGI headers and JSON-only stdout.
* Upstream field names and nesting.

Create contract tests using saved, attributed sample responses from the published API documentation.

Where practical, create optional comparison tests that query the public API only when explicitly enabled with an environment variable. Normal tests must run offline.

Use tolerances for astronomical comparisons and explain why each tolerance is appropriate.

## Required validation

Before completing work, run:

```bash
python -m pytest
python -m compileall src cgi-bin
```

If linting or type checking is added, run those tools as well.

## Documentation requirements

The README must explain:

* Project purpose.
* Compatibility goal and known differences.
* API parameters.
* Standard response fields.
* Extension fields.
* Local development.
* Ephemeris installation.
* Apache CGI deployment.
* Example requests.
* Example JSON.
* Testing.
* File permissions.
* Security considerations.
* Attribution and licensing considerations.
* How to update the ephemeris intentionally.

Do not claim exact compatibility unless tests support the claim.
