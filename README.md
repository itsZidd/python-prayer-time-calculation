# Smart Prayer Times API & CLI

## 🔴 Live Demo
The API is deployed at **https://python-prayer-time-calculation.vercel.app/**.
- Interactive docs (try it in-browser, no setup): https://python-prayer-time-calculation.vercel.app/docs
- Quick health check: https://python-prayer-time-calculation.vercel.app/health
- Example request (coordinates): https://python-prayer-time-calculation.vercel.app/times?lat=-6.2088&lng=106.8456
- Example request (city): https://python-prayer-time-calculation.vercel.app/times?city=Jakarta

## 📖 Overview
This project calculates Islamic prayer times based on latitude, longitude, and timezone. It includes advanced handling for high-latitude locations (like Norway or Sweden) and automatically detects the best calculation method (MWL, ISNA, KEMENAG, etc.) based on the country's coordinates.

## 🗂️ Project Structure
* **`api.py`**: The FastAPI web server. Handles HTTP requests, auto-detects timezones, and reverse-geocodes coordinates to countries.
* **`calculator.py`**: The core math engine. Calculates Julian dates, solar declination, hour angles, and applies high-latitude fallback rules.
* **`config.py`**: Contains all calculation constants. Maps specific angles for Fajr/Isha and links countries to their default local standards.
* **`main.py`**: A Command Line Interface (CLI) to run calculations directly in your terminal.

## 🚀 How to Run

### 1. Run the Web API
Install the required libraries, then start the server:
```
pip install -r requirements.txt
uvicorn api:app --reload
```
Once running, open your browser and go to `http://localhost:8000/docs` to see the interactive API documentation.

### 2. Run the Terminal CLI
To test coordinates quickly in your terminal without starting the server:
```
python main.py
```
Follow the prompts to enter your latitude, longitude, and timezone.

## 🌐 High-Latitude Rules
For locations far enough from the equator that the standard sun-angle calculation for Fajr/Isha has no solution (persistent twilight), pass one of these via `high_latitude_rule`:

| Rule | Behavior |
|---|---|
| `SEVENTH_OF_NIGHT` (default) | Splits the night into 7 parts; Fajr/Isha get the outermost 1/7 on each side. |
| `MIDDLE_OF_NIGHT` | Splits the night in half — the most permissive option. |
| `NEAREST_LATITUDE` | Calculates as if at a lower, more moderate latitude (clamped to 58.5°) — the "Oslo Standard." |
| `TWILIGHT_ANGLE` | Scales the offset proportionally to the method's own twilight angle. |
| `NEAREST_DAY` | Reuses Fajr/Isha's clock time from the nearest day where the calculation *did* have a solution. Stays constant throughout the affected period, then automatically resumes real per-day calculation once it ends. Also known as Aqrab al-Ayyam. |

These only apply when the raw calculation genuinely has no solution — see `CHANGELOG.md` for details on a fix that previously caused this fallback to fire even at moderate latitudes.

**Scope note on `NEAREST_DAY`:** it only ever substitutes Fajr/Isha — never Sunrise/Maghrib. It's built for *persistent twilight* (real sunrise/sunset still happen, but the deeper Fajr/Isha angle can't be reached), not genuine midnight sun (where sunrise/sunset themselves have no solution). See **Limitations** below for why, and for what still returns `N/A` in that more extreme case.

## 🔎 Search by City
`/times` accepts a `city` name as an alternative to `lat`/`lng`:
```
GET /times?city=Jakarta
```
City name matching is offline (via `geonamescache`'s ~34k-city dataset — no external network call, consistent with how the rest of this API avoids live geocoding services). If multiple cities share a name (e.g. "Paris" matches both Paris, France and Paris, Texas), the most populous match is used by default; pass `country` (a name like `Indonesia` or an ISO code like `ID`) to disambiguate:
```
GET /times?city=Paris&country=US
```
The response's `meta.city` field reports exactly which city was matched, so a wrong disambiguation is always visible rather than silent. An unmatched city name returns `404`. If `city` and `lat`/`lng` are both given, `city` takes precedence. Coverage is limited to `geonamescache`'s dataset (populated places above a size threshold) — very small towns may not resolve; use coordinates for those.

## 📡 API Response Example
When you make a GET request to `/times` with coordinates, the API returns a structured JSON response containing the metadata and the calculated prayer times.

**Example Request:**
```
GET http://localhost:8000/times?lat=-6.2088&lng=106.8456&year=2026&month=4&day=2
```

**Example Response** (verified output, not illustrative):
```json
{
  "meta": {
    "date": "2026-04-02",
    "latitude": -6.2088,
    "longitude": 106.8456,
    "city": null,
    "timezone": "Asia/Jakarta",
    "country": "Indonesia",
    "method_used": "KEMENAG",
    "high_lat_rule": "SEVENTH_OF_NIGHT"
  },
  "timings": {
    "Fajr": "04:37",
    "Sunrise": "05:55",
    "Dhuhr": "11:56",
    "Asr": "15:12",
    "Maghrib": "17:57",
    "Isha": "19:06",
    "Midnight": "23:17",
    "Imsak": "04:27"
  }
}
```

## 🧪 Testing
```
pip install pytest httpx
pytest tests/
```
26 tests covering the reference cities from `CHANGELOG.md` (regression guard against reintroducing the 1.1.0/1.2.0 bugs), input validation, city-search resolution/disambiguation, and known edge cases.

## 🎯 Accuracy
Prayer time calculations have been cross-checked against 11 real-world locations spanning every continent and both hemispheres, across 5 calculation methods and 3 unusual timezone offsets (including UTC+5:30 and UTC+5:45), with results matching independent published prayer time sites to within 1-3 minutes — consistent with the normal variance expected between any two independently-implemented astronomical calculators. See `CHANGELOG.md` for details on two calculation bugs found and fixed during this verification.

## 📚 Case Study: Finding and Fixing Two Silent High-Latitude Bugs

This project's calculation engine passed casual testing for months — every low- and mid-latitude city checked out fine. The bugs only surfaced when a companion mobile app (a TypeScript port of this same calculator) was stress-tested against real, independently-published prayer-time references for cities the original testing hadn't covered.

**The first signal** was Tromsø, Norway in July: the calculator returned a Fajr time *before* that same evening's Maghrib — a result that's obviously wrong on its face, since Fajr is supposed to be the following dawn. Tracing through `resolve_time()`, the root cause was a mislabeled variable: `night_duration = 2 * ha_sun` is actually computing the length of *daylight* (the hour angle `ha_sun` runs from solar noon to sunset, so doubling it spans the whole daylight period, not the night). At high latitude in summer this inflated "night duration" to over 21 hours when the real night was only ~2.5 — and that number fed directly into the Fajr/Isha fallback offset.

**The second, more consequential bug** was found by testing a genuinely unremarkable location: New York City in July. A city at 40.7°N has no real high-latitude problem — the direct sun-angle calculation for Fajr should just work. But comparing against a published reference showed the calculator was still quietly overriding a *correct* raw result. The cause: the "safety clamp" meant only for extreme edge cases was running unconditionally on every calculation, for every rule except `NEAREST_LATITUDE`, silently substituting a "safer" value whenever the raw answer was judged too far from sunrise/sunset — regardless of whether anything was actually wrong. [PrayTimes.org's own documentation](http://praytimes.org/wiki/Fajr_and_Isha) confirms these fallback rules are meant to apply *only* when the standard formula has no solution at all, not as a constant sanity check on a working one.

**Methodology used to confirm both fixes were correct, not just different:**
- Re-ran the exact same test cities through a parallel TypeScript port, confirming identical output to the Python fix.
- Cross-checked against multiple independently published prayer-time calculators for cities never used during original development (New York, Winnipeg, Doha, Mumbai, Kathmandu, Nairobi), matching to within 1-3 minutes — the normal variance between any two legitimate implementations.
- Verified the *previously correct* cities (Jakarta, Riyadh) were byte-for-byte unchanged by the fix, confirming it was properly scoped and not a wider behavioral change.
- Built a pytest regression suite pinning all of the above down automatically, so a future change can't silently reintroduce either bug.

**A follow-up code review** (informed by the debugging process above) then surfaced a related design gap: an unrecognized `high_latitude_rule` string silently collapsed Fajr to Sunrise and Isha to Maghrib with no error — because the offset calculation fell through every branch to a default of `0` with nothing catching the miss. That output *looks* plausible (it's a real time, just the wrong one), which is exactly the kind of failure that hides well in production. Fixed with eager validation at construction time, backed by a corrected `config.py` (which was separately missing one of its four documented rule options entirely — `TWILIGHT_ANGLE` — so any validation built against it would have rejected a legitimate rule).

**Feature work following the same rigor:** `NEAREST_DAY` (Aqrab al-Ayyam) was added to handle high-latitude "persistent twilight" — periods where real sunrise/sunset still happen but Fajr/Isha's deeper twilight angle can't be reached. An early version tried extending the same logic to substitute Sunrise/Maghrib too, for genuine midnight-sun locations. That version shipped a real bug during development: Fajr's nearest-valid-day search and Sunrise's independently landed on *different* days, producing a schedule where Fajr appeared after Sunrise. Caught before release by an automated sanity check, and fixed by scoping the feature correctly rather than patching around the symptom — see **Limitations** below for exactly where that boundary sits.

## ⚠️ Limitations

- **Genuine polar day/night still returns `N/A` for every field.** `NEAREST_DAY` only substitutes Fajr/Isha for *persistent twilight* (where plain sunrise/sunset still occur normally). True midnight sun — where the sun never sets at all, common above the Arctic/Antarctic Circle for weeks around the solstice — has no rule that produces a usable answer, by design. Extending `NEAREST_DAY` to cover this case was attempted and reverted after it produced internally inconsistent schedules (see the case study above); a correct fix would need Sunrise/Maghrib's own nearest-valid-day search kept independent of, and reconciled with, Fajr/Isha's — a larger change than has been justified so far given how few locations this affects.
- **Reverse-geocoding degrades silently for remote coordinates.** `reverse_geocode` always returns the *nearest known point*, regardless of actual distance — genuine open-ocean coordinates get attributed to whatever land is nearest, which can be very far away and produce a misleading `country` value. There's no distance/confidence threshold in place to detect and null this out.
- **City search only covers `geonamescache`'s dataset (~34k populated places above a size threshold).** Small towns/villages below that threshold won't resolve and return `404` — use coordinates for those. Ambiguous names default to the most populous match, which is usually but not always what's meant; `meta.city` always reports which one was actually used.
- **Hijri/Islamic calendar dates are not computed by this API at all** — only Gregorian. (The companion mobile app has this via a separate module; it hasn't been ported back here.)
- **No caching or rate limiting** on the API — every request recomputes from scratch and calls the geocoding libraries fresh. Fine for personal/small-scale use; would need attention before any high-traffic deployment.

## requirements.txt
```
fastapi==0.109.0
uvicorn==0.27.0
tzfpy
tzdata
reverse_geocode>=1.4.1
country_converter==1.2.0
geonamescache>=2.0.0
```
`tzdata` provides the IANA timezone database used by `zoneinfo`. It's required on Windows and on minimal Linux images (e.g. Alpine) that don't ship a system tz database — without it, any timezone lookup in `calculator.py` raises `ZoneInfoNotFoundError`. `geonamescache` provides the offline city dataset used by `/times`'s `city` search parameter.
