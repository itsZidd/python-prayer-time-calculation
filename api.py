# api.py
from datetime import datetime
from typing import Optional

import country_converter as coco
import reverse_geocode as rg  # <--- CHANGED: Import the light version (singular)
from fastapi import FastAPI, HTTPException, Query
from geonamescache import GeonamesCache
from tzfpy import get_tz

from calculator import AdvancedPrayerCalculator
from config import HIGH_LATITUDE_RULES

app = FastAPI(title="Smart Prayer Times API")

# Loaded once per function instance (not per-request) — geonamescache holds
# its ~34k-city dataset in memory, so this avoids re-parsing it on every call.
_geo_cache = GeonamesCache()


def resolve_city(city: str, country: Optional[str]):
    """
    Resolves a city name to its best-matching record via geonamescache
    (offline dataset — no network call, consistent with how this API
    already does reverse geocoding).

    Tries an exact name match first, then falls back to substring search
    for partial names (e.g. "New York City" -> "New York"). If multiple
    cities share the name, `country` (accepted as either a name like
    "Indonesia" or an ISO code like "ID") filters to that country; ties
    are broken by picking the most populous match, since that's almost
    always what a user means by an unqualified city name (e.g. "Paris"
    should resolve to Paris, France, not Paris, Texas).

    Returns None if nothing matches.
    """
    matches = _geo_cache.search_cities(
        city, attribute="name", case_sensitive=False, contains_search=False
    )
    if not matches:
        matches = _geo_cache.search_cities(
            city, attribute="name", case_sensitive=False, contains_search=True
        )
    if not matches:
        return None

    if country:
        code = coco.convert(names=country, to="ISO2")
        if code and code != "not found":
            filtered = [m for m in matches if m["countrycode"] == code]
            if filtered:
                matches = filtered

    return max(matches, key=lambda m: int(m.get("population") or 0))


@app.get("/")
def root():
    return {
        "status": "ok",
        "docs": "/docs",
        "example": "/times?lat=-6.2088&lng=106.8456",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/times")
def get_prayer_times(
    lat: Optional[float] = Query(
        None, ge=-90, le=90, description="Latitude, -90 to 90. Required unless 'city' is given."
    ),
    lng: Optional[float] = Query(
        None, ge=-180, le=180, description="Longitude, -180 to 180. Required unless 'city' is given."
    ),
    city: Optional[str] = Query(
        None,
        description=(
            "City name to search instead of lat/lng, e.g. 'Jakarta'. "
            "Takes precedence over lat/lng if both are given."
        ),
    ),
    country: Optional[str] = Query(
        None,
        description=(
            "Optional country name or ISO code to disambiguate cities that "
            "share a name (e.g. 'Paris'), such as 'Indonesia' or 'ID'. Only "
            "used together with 'city'."
        ),
    ),
    high_latitude_rule: str = Query(
        "SEVENTH_OF_NIGHT",
        description=(
            "Options: SEVENTH_OF_NIGHT (default), MIDDLE_OF_NIGHT, "
            "NEAREST_LATITUDE (use for Norway/Sweden), TWILIGHT_ANGLE"
        ),
    ),
    year: int = None,
    month: int = None,
    day: int = None,
):
    """
    Fetches daily prayer times for a specific location, given either
    coordinates (`lat`/`lng`) or a `city` name.
    - **Smart Detection**: Automatically detects the timezone and country based on the coordinates.
    - **Method Selection**: Selects the appropriate calculation method (e.g., KEMENAG for Indonesia, MWL for Europe).
    - **High Latitude Safeties**: Applies fallback rules (like 1/7th of the night) if coordinates are in extreme regions where the sun doesn't set.
    """
    # FIX: validate against the actual supported rules (via config.py — the
    # single source of truth also used by the calculator) BEFORE it reaches
    # AdvancedPrayerCalculator. `lat`/`lng` are now range-validated directly
    # by FastAPI's Query(ge=..., le=...), returning a proper 422 for garbage
    # coordinates instead of letting them flow into the astronomy functions.
    if high_latitude_rule not in HIGH_LATITUDE_RULES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid high_latitude_rule: {high_latitude_rule!r}. "
                f"Valid options are: {', '.join(sorted(HIGH_LATITUDE_RULES.keys()))}"
            ),
        )

    # --- Resolve city -> coordinates, or require coordinates directly ---
    matched_city = None
    if city:
        match = resolve_city(city, country)
        if match is None:
            detail = f"No city found matching {city!r}"
            if country:
                detail += f" in {country!r}"
            raise HTTPException(status_code=404, detail=detail)
        lat = match["latitude"]
        lng = match["longitude"]
        matched_city = {
            "name": match["name"],
            "country_code": match["countrycode"],
            "population": match["population"],
        }
    elif lat is None or lng is None:
        raise HTTPException(
            status_code=422,
            detail="Provide either 'city' (optionally with 'country') or both 'lat' and 'lng'.",
        )

    # --- Geocoding / timezone detection ---
    # FIX: this used to be inside the same broad try/except as the
    # calculation itself, so any failure here (or a "close enough" bad
    # match) got reported as an opaque 500. Neither of these libraries
    # actually raises for bad input in practice — get_tz can return None/""
    # for coordinates with no timezone match, reverse_geocode always returns
    # its NEAREST known point regardless of how far away it actually is
    # (e.g. genuine open-ocean coordinates silently get attributed to
    # whatever land is nearest, which can be thousands of km off), and
    # country_converter returns the literal string "not found" rather than
    # raising for an unmapped code. None of these are exceptions to catch —
    # they're low-confidence results to handle explicitly.
    try:
        timezone = get_tz(lng=lng, lat=lat)
        if not timezone:
            timezone = "UTC"

        if matched_city:
            # Country is already known directly from the city match — more
            # reliable than reverse-geocoding back from coordinates, and
            # avoids a redundant nearest-point lookup.
            converted = coco.convert(names=matched_city["country_code"], to="name_short")
            country_name = converted if converted and converted != "not found" else None
        else:
            location_data = rg.search([(lat, lng)])[0]
            country_code = location_data.get("country_code")

            country_name = None
            if country_code:
                converted = coco.convert(names=country_code, to="name_short")
                if converted and converted != "not found":
                    country_name = converted
    except Exception as e:
        # A genuine failure in the geocoding libraries themselves (not a bad
        # match, an actual exception) — still worth a clear 502, since it's
        # an upstream dependency issue, not something wrong with the request.
        raise HTTPException(
            status_code=502, detail=f"Location lookup failed: {e}"
        )

    # --- Date ---
    if year and month and day:
        try:
            calc_date = datetime(year, month, day)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Invalid date: {e}")
    else:
        calc_date = datetime.now()

    # --- Calculation ---
    try:
        calc = AdvancedPrayerCalculator(
            lat=lat,
            lng=lng,
            timezone=timezone,
            country=country_name,
            high_latitude_rule=high_latitude_rule,
        )
        times = calc.get_times(calc_date)
    except ValueError as e:
        # e.g. AdvancedPrayerCalculator's own high_latitude_rule validation —
        # redundant with the check above in normal use, but keeps this
        # endpoint correct even if that check is ever bypassed or the
        # calculator is called with a rule this endpoint didn't anticipate.
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # A genuinely unexpected failure in the calculation itself.
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "meta": {
            "date": calc_date.strftime("%Y-%m-%d"),
            "latitude": lat,
            "longitude": lng,
            "city": matched_city,  # null when queried by lat/lng directly; shows which city matched otherwise
            "timezone": timezone,
            "country": country_name,  # null if genuinely undetectable (e.g. open ocean)
            "method_used": calc.method_key,
            "high_lat_rule": high_latitude_rule,
        },
        "timings": times,
    }
