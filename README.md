# 🕌 Smart Prayer Times API & Calculation Engine

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-0.27.0-499848?style=for-the-badge&logo=gunicorn&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-Serverless-000000?style=for-the-badge&logo=vercel&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-26_Passed-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)

An astronomical Islamic prayer time calculator and lightweight REST API built with Python, FastAPI, and offline geocoding. It computes accurate daily prayer schedules worldwide using celestial hour angles, automatic timezone and calculation convention detection, and dedicated high-latitude fallback rules for extreme regions.

Live instance: [https://python-prayer-time-calculation.vercel.app/](https://python-prayer-time-calculation.vercel.app/) | Interactive Swagger Docs: [/docs](https://python-prayer-time-calculation.vercel.app/docs)

---

## 🚀 What's Built

### 🌐 1. REST API & Geocoding Services

- **FastAPI HTTP Endpoints**: Serves `GET /` (service metadata), `GET /health` (liveness probe), and `GET /times` (prayer time calculation) deployed serverlessly via `@vercel/python` in [`vercel.json`](./vercel.json) and [`api.py`](./api.py#L57-L111).
- **Offline City Search & Disambiguation**: Resolves city queries in `resolve_city()` against `geonamescache`'s ~34k-city in-memory dataset, filters by optional `country` via `country_converter`, and breaks ties by selecting the highest population match ([`api.py:resolve_city`](./api.py#L21-L55)).
- **Coordinate Geocoding & Timezone Detection**: Automatically resolves `(lat, lng)` coordinates to IANA timezones via Rust-backed `tzfpy.get_tz()` (fallback to UTC) and short country names via `reverse_geocode` and `country_converter` ([`api.py:get_prayer_times`](./api.py#L148-L187)).
- **Input & Range Validation**: Validates latitude (`-90` to `90`), longitude (`-180` to `180`), calculation dates, and rule names against `HIGH_LATITUDE_RULES`, returning standard `404`, `422`, and `502` HTTP status codes ([`api.py:get_prayer_times`](./api.py#L117-L147)).

### 🧮 2. Astronomical Calculation Engine

- **Celestial Math & Solar Position**: Converts Gregorian dates to Julian Dates via `calculate_julian_date()` and computes solar declination and Equation of Time (EqT) via `sun_position()` ([`calculator.py`](./calculator.py#L78-L120)).
- **8 Daily Prayer & Astronomical Times**: Calculates Fajr, Sunrise, Dhuhr (solar noon), Asr, Maghrib, Isha, Midnight (sunset-to-Fajr midpoint), and Imsak (Fajr minus 10 minutes) formatted as `HH:MM` ([`calculator.py:get_times`](./calculator.py#L265-L376)).
- **Asr Juristic Madhab Calculation**: Computes Asr shadow angles via `get_asr_angle()`, supporting both `STANDARD` (Shafi'i, Maliki, Hanbali / shadow factor 1.0) and `HANAFI` (shadow factor 2.0) ([`calculator.py:get_asr_angle`](./calculator.py#L139-L150)).
- **17 Worldwide Calculation Conventions**: Maps 17 global calculation authorities (MWL, ISNA, Egypt, KEMENAG, Singapore, JAKIM, Makkah, Qatar, Kuwait, Dubai, Tehran, Turkey, France UOIF/15°, Russia, London, Karachi) and 40+ country defaults in [`config.py`](./config.py#L4-L144).

### ❄️ 3. High-Latitude & Extreme Region Safeties

- **5 High-Latitude Fallback Rules**: Implements `SEVENTH_OF_NIGHT` (1/7th partition), `MIDDLE_OF_NIGHT` (1/2 partition), `NEAREST_LATITUDE` (clamps latitude to 58.5° Oslo Standard), `TWILIGHT_ANGLE` (angle/60 proportional scale), and `NEAREST_DAY` in [`calculator.py:resolve_time`](./calculator.py#L187-L263).
- **Aqrab al-Ayyam (`NEAREST_DAY`) Search**: Performs bidirectional day-by-day scanning up to 190 days via `find_nearest_valid_time()` during persistent twilight to anchor Fajr and Isha to the closest calculable date while keeping times constant throughout the twilight period ([`calculator.py:find_nearest_valid_time`](./calculator.py#L158-L186)).
- **Polar Day/Night Safety**: Detects missing sunrise solutions (`ha_sunrise is None`) under true midnight sun / polar night and outputs structured `"N/A (Polar)"` indicators across all prayer fields ([`calculator.py:get_times`](./calculator.py#L285-L299)).

### 💻 4. Interactive CLI & Test Suite

- **Interactive Terminal CLI**: Prompts for coordinates, IANA timezone strings, and optional country names to print formatted daily prayer schedules directly to the terminal ([`main.py`](./main.py#L7-L70)).
- **26-Test Pytest Suite**: Full regression coverage verifying reference cities (Jakarta, Riyadh, New York City, Tromsø, Tehran), rule validations, polar edge cases, and API city search queries ([`tests/test_api.py`](./tests/test_api.py), [`tests/test_calculator.py`](./tests/test_calculator.py)).

---

## 🛠️ Tech Stack & Complete Tools Inventory

### 📦 Exhaustive Tools & Libraries Breakdown (Grouped by Role)

#### 1. Core Web Framework & HTTP Server

| Package | Version | Purpose & Usage |
| :--- | :--- | :--- |
| **`fastapi`** | `0.109.0` | Powers the web API application, route decorators (`GET /times`, `/health`, `/`), OpenAPI schema generation, and query parameter validation in [`api.py`](./api.py). |
| **`uvicorn`** | `0.27.0` | ASGI web server used to run the FastAPI application in local development and production environments. |

#### 2. Geocoding, Geographic Data & Timezone Resolution

| Package | Version | Purpose & Usage |
| :--- | :--- | :--- |
| **`geonamescache`** | `>=2.0.0` | In-memory database of ~34,000 global cities used by `resolve_city()` for fast offline city search and disambiguation without external HTTP calls in [`api.py`](./api.py#L18). |
| **`tzfpy`** | *(latest)* | Fast Rust-compiled binary timezone finder used in `get_tz(lng, lat)` to resolve coordinates to IANA timezone names in [`api.py`](./api.py#L161). |
| **`tzdata`** | *(latest)* | Provides the IANA timezone database files required by Python's standard `zoneinfo` module across Windows and minimal Linux container environments. |
| **`reverse_geocode`** | `>=1.4.1` | Lightweight offline reverse-geocoding library used to map `(lat, lng)` tuples to ISO country codes in [`api.py`](./api.py#L172). |
| **`country_converter`** | `1.2.0` | Normalizes and converts country names and ISO2/ISO3 codes to standardized short names in [`api.py`](./api.py#L48-L177). |

#### 3. Astronomical Math & Runtime Standard Libraries

| Package | Version | Purpose & Usage |
| :--- | :--- | :--- |
| **`math`** | *(Python stdlib)* | Provides trigonometric functions (`sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `radians`, `degrees`, `floor`) for solar declination and hour-angle calculation in [`calculator.py`](./calculator.py#L72-L150). |
| **`datetime`** | *(Python stdlib)* | Manages Gregorian date parsing, day stepping for Julian dates, and timedelta offsets in [`calculator.py`](./calculator.py#L175-L185) and [`api.py`](./api.py#L189-L196). |
| **`zoneinfo`** | *(Python stdlib)* | Handles IANA timezone instantiation and UTC offset computation via `ZoneInfo.utcoffset()` in [`calculator.py:get_times`](./calculator.py#L267-L271). |

#### 4. Testing & Verification

| Package | Version | Purpose & Usage |
| :--- | :--- | :--- |
| **`pytest`** | `^7.0.0` / `^8.0.0` | Test runner executing unit tests and regression assertions across astronomy math, reference cities, and API endpoints in [`tests/`](./tests/). |
| **`httpx`** | `^0.24.0` | HTTP client library providing FastAPI `TestClient` transport support for endpoint testing in [`tests/test_api.py`](./tests/test_api.py#L13-L17). |

#### 5. Deployment & Cloud Hosting

| Package | Version | Purpose & Usage |
| :--- | :--- | :--- |
| **`@vercel/python`** | *(Vercel Builder)* | Serverless runtime builder executing [`api.py`](./api.py) on Vercel's global edge infrastructure as configured in [`vercel.json`](./vercel.json). |

---

## 📖 Engineering Notes

### 🌓 1. Fixing the Inverted Daylight vs. Night Duration in High-Latitude Fallbacks

In earlier versions, `resolve_time()` calculated night length using `night_duration = 2 * ha_sun`. Because the solar hour angle `ha_sun` represents the duration from solar noon to sunset, multiplying it by two measures total *daylight length*, not night length. In summer at high latitudes (e.g., Tromsø, Norway at 69.6°N in late July), daylight spans over 21.5 hours while actual night is only ~2.5 hours. Treating 21.5 hours as the night duration drastically inflated the fallback offset, leading to astronomical absurdities such as Fajr calculating to a clock time *before* that same evening's Maghrib.

The solution in [`calculator.py:resolve_time`](./calculator.py#L226-L235) corrected the formula to `night_duration = 24 - (2 * ha_sun)`. This ensured fallback fractions (such as 1/7th of the night) scaled against the true dark window between sunset and sunrise.

### 🎯 2. Eliminating the Over-Aggressive Safety Clamp at Moderate Latitudes

An early implementation attempted to prevent bad outputs by passing every calculated Fajr and Isha time through a night-fraction "safety clamp," overriding values that diverged beyond fixed boundaries. While intended for extreme conditions, this clamp ran unconditionally across all rules (except `NEAREST_LATITUDE`) even for moderate locations where direct sun angles were completely valid. For example, in New York City (40.7°N) in July, the mathematically correct 15° ISNA Fajr calculation of `04:20` was silently overridden and shifted to `03:45`/`04:08`.

Following documented astronomical standards from [PrayTimes.org](http://praytimes.org/wiki/Fajr_and_Isha), high-latitude fallbacks are intended *strictly* when raw trigonometric formulas have no solution (`cos_h` outside `[-1, 1]`). The logic in [`calculator.py:resolve_time`](./calculator.py#L250-L262) was updated to trust any non-`None` raw calculation directly, reserving fallback offsets exclusively for dates where `initial_time is None`.

### 🧭 3. Constraining `NEAREST_DAY` (Aqrab al-Ayyam) Scope to Prevent Search Divergence

When adding the `NEAREST_DAY` rule to resolve persistent twilight in northern regions, an initial prototype attempted to generalize the algorithm by substituting Sunrise and Maghrib in addition to Fajr and Isha for polar midnight sun conditions. However, because Fajr (18° below horizon) and Sunrise (0.833° below horizon) lose their mathematical solutions on different calendar days as the sun's declination shifts, their independent searches landed on divergent reference dates. This caused a schedule inversion where substituted Fajr occurred *after* substituted Sunrise.

Rather than introducing heuristic patches, the scope was aligned with traditional fiqh principles: `find_nearest_valid_time()` in [`calculator.py`](./calculator.py#L158-L186) is scoped strictly to Fajr and Isha for persistent twilight. Genuine polar day and night (where sunrise itself has no solution) cleanly and consistently return `"N/A (Polar)"`.

### ⚡ 4. Hardening Geocoding Invariants and API Status Codes

During API hardening, an audit revealed that `reverse_geocode` does not raise exceptions for open-ocean coordinates; instead, it silently matches the nearest known terrestrial point regardless of thousands of kilometers of ocean distance. Similarly, `country_converter` returned the literal string `"not found"` rather than raising an error, which was previously leaking into API responses as a valid country name. Furthermore, broad `except Exception` blocks were masking client validation errors as opaque `500 Internal Server Error` responses.

In [`api.py:get_prayer_times`](./api.py#L117-L215), coordinate boundaries (`Query(ge=-90, le=90)`) and rule validation against `HIGH_LATITUDE_RULES` were placed directly on FastAPI query parameters. Unmapped country codes are explicitly sanitized to `null`, upstream geocoding errors map to `502 Bad Gateway`, invalid parameters return `422 Unprocessable Entity`, and unknown city lookups return `404 Not Found`.

---

## ⚠️ Known Limitations

1. **Genuine Polar Day/Night Returns `N/A (Polar)`**:
   - For locations experiencing true midnight sun or polar night where the sun does not cross `-0.8333°` (e.g., Longyearbyen, Svalbard in June), `get_times()` returns `"N/A (Polar)"` for all prayer fields. The only rule that returns clock times under midnight sun is `NEAREST_LATITUDE`, which clamps the latitude input to 58.5° before astronomical calculation begins.
2. **Reverse-Geocoding Nearest-Point Distance Degradation**:
   - `reverse_geocode` uses an offline spatial KD-tree without a maximum distance threshold. Coordinates in remote international waters or oceanic trenches will be attributed to the nearest coastline or island territory rather than returning empty metadata.
3. **Offline City Dataset Scope & Disambiguation Threshold**:
   - City lookups in `resolve_city()` are limited to `geonamescache`'s ~34,000-city dataset (populated places above threshold sizes). Small unincorporated towns or villages not in the dataset return `404` and require coordinate-based queries. Shared names default to the largest population center unless the `country` query parameter is provided.
4. **Gregorian Calendar Support Only**:
   - The engine computes prayer schedules exclusively for Gregorian dates (`datetime(year, month, day)`). Islamic lunar Hijri dates (such as Ramadan 1st) are not computed or converted by this backend.
5. **Stateless Uncached Execution**:
   - The API does not maintain an in-memory or Redis caching layer for repeated lookups. Every HTTP request re-computes Julian dates, solar declination, and geocoding lookups on demand.

---

## 🚀 Local Setup & Deployment

### Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start local development server
uvicorn api:app --reload

# 3. Run interactive terminal CLI
python main.py

# 4. Run automated test suite
pip install pytest httpx
pytest tests/
```

### Vercel Serverless Deployment

1. Install the Vercel CLI via `npm install -g vercel` or link the repository to the [Vercel Dashboard](https://vercel.com).
2. Ensure [`vercel.json`](./vercel.json) is present in the project root containing the `@vercel/python` build configuration.
3. Deploy to production:
   ```bash
   vercel --prod
   ```

---

## 📁 Project Structure

```text
python-prayer-time-calculation/
├── api.py              # FastAPI web application, endpoint handlers, and geocoding logic
├── calculator.py       # Core astronomical engine, Julian date math, and high-latitude rules
├── config.py           # Calculation methods (angles), country defaults, and rule registries
├── main.py             # Interactive CLI script for terminal prayer time calculations
├── requirements.txt    # Production Python dependencies and pinned packages
├── vercel.json         # Vercel serverless routing and Python runtime configuration
├── tests/
│   ├── test_api.py         # Pytest suite for FastAPI endpoints, city search, and validation
│   └── test_calculator.py # Pytest suite for astronomical math, reference cities, and polar rules
├── CHANGELOG.md        # Historical record of releases, bug fixes, and feature additions
├── LICENCE             # MIT Open Source License
└── README.md           # Project documentation, tools inventory, and engineering notes
```

---

## 📝 Changelog

See [CHANGELOG.md](./CHANGELOG.md) for the full history of releases, fixes, and changes.
