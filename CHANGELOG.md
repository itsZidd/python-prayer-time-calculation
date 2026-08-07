# Changelog

All notable changes to this project are documented here.

## [1.4.0] - 2026-08-07

### Added

- **City search on `/times`.** The endpoint now accepts a `city` name (e.g. `?city=Jakarta`) as an alternative to `lat`/`lng`. Resolution is offline via `geonamescache`'s ~34k-city dataset — no external network call, consistent with how the rest of this API already avoids live geocoding services. Ambiguous names (e.g. "Paris" matches both France and Texas) default to the most populous match; an optional `country` param (name or ISO code) disambiguates explicitly. The response's `meta.city` field always reports exactly which city was matched, so a wrong disambiguation is visible rather than silent. Unmatched names return `404`; if both `city` and `lat`/`lng` are given, `city` takes precedence. Added `tests/test_api.py` (7 tests) covering resolution, disambiguation, and error cases.

## [1.3.0] - 2026-08-07

### Added

- **`NEAREST_DAY` high-latitude rule (Aqrab al-Ayyam / "Nearest Valid Day").** For locations experiencing persistent twilight — real sunrise/sunset still occur, but Fajr/Isha's deeper sun-angle threshold can't be reached — this rule reuses the closest day's Fajr/Isha clock time instead of falling back to a night-fraction estimate. The substituted value stays constant throughout the affected period and automatically resumes real per-day calculation once the angle becomes reachable again, with no manual intervention needed.

  New method: `AdvancedPrayerCalculator.find_nearest_valid_time()` searches outward day-by-day (both directions) from the target date for the nearest day where the given sun angle has a solution.

  `config.HIGH_LATITUDE_RULES` updated to include `"NEAREST_DAY"`.

  **Scope, deliberately narrow:** this rule only ever substitutes Fajr/Isha — never Sunrise/Maghrib. An earlier version during development tried extending it to cover genuine midnight-sun cases (where even plain sunrise/sunset has no solution) by substituting those too, and it shipped a real bug: Fajr's nearest-valid-day search and Sunrise's independently landed on different days, producing schedules where Fajr appeared after Sunrise. Caught by an automated sanity check before release. Reverted to the narrower, correctly-scoped version — genuine polar day/night still returns `N/A` for every field, matching the behavior of every other rule except `NEAREST_LATITUDE` (which sidesteps the issue by clamping latitude before any calculation runs, not by actually handling it). See `README.md`'s Limitations section for the full reasoning.

### Verification

- Tested across a full season transition at Longyearbyen, Svalbard (78.2°N): correctly `N/A` during genuine midnight sun (through ~August), then a stable substituted Fajr/Isha through the persistent-twilight period (verified identical across two different dates three weeks apart), then automatic return to real per-day calculation once the 18° angle becomes reachable again in October.
- Cross-verified against the same feature in the companion TypeScript/mobile-app port — identical output for every test case above.
- 3 new dedicated pytest tests added (`test_nearest_day_*`), plus the existing parametrized rule-acceptance test automatically covers `NEAREST_DAY` now that it's in `config.HIGH_LATITUDE_RULES`. 25 tests total, all passing.

## [1.2.0] - 2026-08-07

### Fixed

- **Invalid `high_latitude_rule` silently gave a wrong answer.** A typo'd or unrecognized rule string fell through every branch of `resolve_time()`'s offset calculation with no error, leaving `offset = 0`. This collapsed Fajr to Sunrise and Isha to Maghrib with no indication anything was wrong — and it only manifested for locations where the raw calculation has no solution, i.e. exactly the high-latitude cases this logic exists to help.

  **Fix:** `AdvancedPrayerCalculator.__init__` now validates `high_latitude_rule` against `config.HIGH_LATITUDE_RULES` and raises `ValueError` immediately for anything unrecognized. `api.py` also validates the query param before it ever reaches the calculator, returning `422` instead of either a silent wrong answer or an opaque `500`.

- **`config.HIGH_LATITUDE_RULES` was missing `"TWILIGHT_ANGLE"`**, even though `calculator.py` has always supported it and the README documents it. This meant any validation built against that dict (see above) would have incorrectly rejected a legitimate, working rule.

  **Fix:** added to the dict.

- **`api.py` had no input validation and swallowed all failures into a generic `500`.**
  - `lat`/`lng` had no range checking — out-of-range values flowed straight into the astronomy functions.
  - `reverse_geocode` doesn't fail for ocean coordinates — it returns the *nearest known land point* regardless of distance, which can silently attribute a wildly wrong country to genuinely remote coordinates.
  - `country_converter.convert()` doesn't raise for an unmapped country code — it returns the literal string `"not found"`, which was previously passed straight through into the API response's `"country"` field, looking like a real (wrong) value rather than an absence of one.
  - Every exception, regardless of cause, was caught by one broad `except Exception` and reported as `500 Internal Server Error` — including client-input errors that should have been `422`.

  **Fix:** `lat`/`lng` now use FastAPI's built-in `Query(ge=..., le=...)` range validation. `high_latitude_rule` is validated explicitly (`422`). An unmapped/low-confidence country now resolves to `null` in the response rather than the string `"not found"`. Genuine geocoding-library exceptions are now reported as `502` (upstream dependency issue) rather than `500`. Calculator-side `ValueError`s (e.g. the new rule validation, as a defense-in-depth backstop) map to `422`. A true `500` is now reserved for genuinely unexpected server-side failures.

- **Added a pytest suite** (`tests/test_calculator.py`, `tests/test_api.py`) covering the reference cities from the 1.1.0 changelog entry (so a regression in `resolve_time()` gets caught automatically), the `TWILIGHT_ANGLE` config gap, the invalid-rule validation, and both API-level validation paths. 21 tests, run with `pytest tests/`.

### Known limitation at the time of this release (addressed in part by 1.3.0)

- **Genuine polar day/night returned `N/A` for every prayer regardless of which `high_latitude_rule` was picked**, except `NEAREST_LATITUDE` — which only "worked" there because it clamps `self.lat` to 58.5° *before* any calculation runs, so by the time the polar check happens, the calculator is no longer looking at the real latitude at all. `SEVENTH_OF_NIGHT`, `MIDDLE_OF_NIGHT`, and `TWILIGHT_ANGLE` had no mechanism to produce a usable answer for locations with true midnight sun (e.g. Svalbard in June), even though these are the commonly-selected rules for high-latitude use.

  **Update:** 1.3.0 adds `NEAREST_DAY` for the related-but-distinct *persistent twilight* case (real sunrise/sunset, but Fajr/Isha's angle unreachable). Genuine midnight sun — where even plain sunrise/sunset has no solution — remains unresolved by design; see `README.md`'s Limitations section for why extending `NEAREST_DAY` to cover it isn't a straightforward fix.

## [1.1.0] - 2026-08-07

### Fixed

- **`night_duration` was computing daylight length, not night length.**
  `resolve_time()` calculated `night_duration = 2 * ha_sun`, where `ha_sun` is the hour angle from solar noon to sunrise/sunset — so `2 * ha_sun` is actually the length of *daylight*. The true night length is `24 - (2 * ha_sun)`.

  This was most visible at high latitude in summer: for a location like Tromsø, Norway in late July, the old formula computed "night" as ~21.5 hours when the real night was only ~2.5 hours. That inflated value fed into the Fajr/Isha fallback offset, producing nonsensical results — e.g. a calculated "Fajr" landing *before* that same evening's Maghrib.

  **Fix:** `night_duration = 24 - (2 * ha_sun)`.

- **The high-latitude "safety clamp" was overriding valid calculations even at moderate latitudes.**
  Previously, `resolve_time()` applied a clamp to *every* successfully-calculated Fajr/Isha time (for all rules except `NEAREST_LATITUDE`), comparing it against a night-fraction boundary and silently substituting a "safer" value if the raw result was judged too far from sunrise/sunset. This logic ran unconditionally, regardless of whether the location actually had any high-latitude problem.

  In practice this meant even non-extreme locations could get a subtly wrong answer. Verified case: New York City (40.7°N) in July — the correct, direct 15° sun-angle calculation for Fajr gives `04:20` (confirmed against an independent published prayer-time reference), but the old clamp logic overrode this to `03:45`/`04:08` depending on which other bug was also present, moving it further from the correct answer.

  Per [PrayTimes.org's own documented rationale](http://praytimes.org/wiki/Fajr_and_Isha), these high-latitude fallback rules exist specifically for when *"the determination of Fajr and Isha is not possible using the usual formulas"* — i.e., only when the raw calculation has no solution at all — not as a constant sanity-check on an already-valid answer.

  **Fix:** the fallback/clamp logic in `resolve_time()` is now only invoked when the raw calculation returns `None`. A valid raw calculation is always trusted directly, for every high-latitude rule.

- **Maghrib could fail for methods with a non-default `maghrib_angle`.**
  Most methods use the default `maghrib_angle` (0.8333°, i.e. plain sunset), which always has a solution whenever sunrise does. But methods with a deeper angle — e.g. `TEHRAN`'s Shia-convention 4.5° — can fail to resolve even when plain sunset succeeds. Previously this wasn't handled at all, and would have raised a `TypeError` (`dhuhr + None`) at high enough latitude with that method.

  **Fix:** Maghrib now falls back through the same `resolve_time()` logic as Fajr/Isha when its angle has no solution, anchored to the physical sunset time.

### Verification

All three fixes were checked against:
- A regression suite of previously-correct low/mid-latitude locations (Jakarta, Riyadh) — confirmed byte-for-byte unchanged.
- Independent published prayer-time references for New York, Winnipeg, Doha, Mumbai, Kathmandu, Nairobi, and others — matching to within 1-3 minutes (normal variance between independently-implemented calculators).
- A direct comparison of the raw (unclamped) sun-angle calculation against the old clamped output, confirming the fix moves results *toward* the mathematically correct answer, not away from it.
- A parallel TypeScript port of this calculator (used in a companion mobile app), cross-verified to produce identical output for every test case above.

None of these fixes change the public API (`AdvancedPrayerCalculator`'s constructor signature and `get_times()` return shape are unchanged) — only the internal calculation in `resolve_time()` and the Maghrib resolution in `get_times()`.

## [1.0.0] - Initial release

- Prayer time calculation via solar declination and hour-angle astronomy (Julian date → sun position → hour angles → Fajr/Sunrise/Dhuhr/Asr/Maghrib/Isha/Midnight/Imsak).
- 17 built-in calculation methods (MWL, ISNA, Egypt, KEMENAG, Singapore, JAKIM, Makkah, Qatar, Kuwait, Dubai, Tehran, Turkey, France (UOIF/15°), Russia, London, Karachi).
- Automatic method selection based on country.
- High-latitude fallback rules: `SEVENTH_OF_NIGHT`, `MIDDLE_OF_NIGHT`, `NEAREST_LATITUDE`, `TWILIGHT_ANGLE`.
- Standard vs. Hanafi Asr madhab support.
- FastAPI web server (`api.py`) with automatic timezone/country detection from coordinates.
- CLI tool (`main.py`) for quick terminal-based calculations.
