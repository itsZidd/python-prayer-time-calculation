# api.py
from datetime import datetime

import country_converter as coco
import reverse_geocode as rg  # <--- CHANGED: Import the light version (singular)
from fastapi import FastAPI, HTTPException, Query
from timezonefinder import TimezoneFinder

from calculator import AdvancedPrayerCalculator

app = FastAPI(title="Smart Prayer Times API")
tf = TimezoneFinder()


@app.get("/times")
def get_prayer_times(
    lat: float,
    lng: float,
    high_latitude_rule: str = Query(
        "SEVENTH_OF_NIGHT",
        description="Options: SEVENTH_OF_NIGHT (Default), NEAREST_LATITUDE (Use for Norway/Sweden)",
    ),
    year: int = None,
    month: int = None,
    day: int = None,
):
    try:
        # 1. Auto-detect Timezone
        timezone = tf.timezone_at(lng=lng, lat=lat)
        if not timezone:
            timezone = "UTC"

        # 2. Auto-detect Country (UPDATED FOR LIGHT LIBRARY)
        # reverse_geocode.search expects a list of tuples: [(lat, lng)]
        # It returns a list of dicts: [{'country_code': 'NO', 'city': 'Tromsø'}]
        location_data = rg.search([(lat, lng)])[0]
        country_code = location_data["country_code"]  # Returns 'NO', 'ID', etc.

        # Convert 'NO' -> 'Norway' for our calculator config
        country_name = coco.convert(names=country_code, to="name_short")

        # 3. Date
        if year and month and day:
            calc_date = datetime(year, month, day)
        else:
            calc_date = datetime.now()

        # 4. Initialize Calculator
        calc = AdvancedPrayerCalculator(
            lat=lat,
            lng=lng,
            timezone=timezone,
            country=country_name,
            high_latitude_rule=high_latitude_rule,
        )

        times = calc.get_times(calc_date)

        return {
            "meta": {
                "date": calc_date.strftime("%Y-%m-%d"),
                "latitude": lat,
                "longitude": lng,
                "timezone": timezone,
                "country": country_name,
                "method_used": calc.method_key,
                "high_lat_rule": high_latitude_rule,
            },
            "timings": times,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
