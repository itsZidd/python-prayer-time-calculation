# calculator.py
import math
from zoneinfo import ZoneInfo

from config import CALCULATION_METHODS, COUNTRY_METHOD_MAPPING, HIGH_LATITUDE_RULES


class AdvancedPrayerCalculator:
    def __init__(
        self,
        lat,
        lng,
        timezone,
        country=None,
        method=None,
        asr_madhab="STANDARD",
        high_latitude_rule=None,
    ):
        self.lat = lat
        self.lng = lng
        self.timezone_input = timezone
        self.asr_madhab = asr_madhab
        # Default to SEVENTH_OF_NIGHT if nothing is passed
        self.high_latitude_rule = (
            high_latitude_rule if high_latitude_rule else "SEVENTH_OF_NIGHT"
        )

        # --- HIGH LATITUDE LOGIC ---

        # RULE: NEAREST LATITUDE (Aqrab Al-Bilad)
        # Clamps latitude to 58.5 degrees.
        # This simulates the "Oslo Standard" used by mosques in Tromsø.
        if self.high_latitude_rule == "NEAREST_LATITUDE":
            MAX_LAT = 58.5  # <--- Tuned from 60.0 to 58.5 for better accuracy
            if self.lat > MAX_LAT:
                self.lat = MAX_LAT
            elif self.lat < -MAX_LAT:
                self.lat = -MAX_LAT

        # ---------------------------

        # Auto-detect Method (MWL, ISNA, etc.)
        if country and not method:
            clean_country = country.lower().strip()
            self.method_key = COUNTRY_METHOD_MAPPING.get(clean_country, "MWL")
        else:
            self.method_key = method if method else "MWL"

        self.config = CALCULATION_METHODS.get(
            self.method_key, CALCULATION_METHODS["MWL"]
        )
        self.fajr_angle = self.config.get("fajr_angle", 18.0)
        self.isha_angle = self.config.get("isha_angle", 18.0)
        self.maghrib_angle = self.config.get("maghrib_angle", 0.8333)
        self.isha_fixed = self.config.get("isha_fixed_minutes", None)

    # --- Math Helpers ---
    def rad(self, d):
        return math.radians(d)

    def deg(self, r):
        return math.degrees(r)

    def calculate_julian_date(self, year, month, day):
        if month <= 2:
            year -= 1
            month += 12
        a = math.floor(year / 100)
        b = 2 - a + math.floor(a / 4)
        return (
            math.floor(365.25 * (year + 4716))
            + math.floor(30.6001 * (month + 1))
            + day
            + b
            - 1524.5
        )

    def sun_position(self, jd):
        D = jd - 2451545.0
        g = 357.529 + 0.98560028 * D
        q = 280.459 + 0.98564736 * D
        L = q + 1.915 * math.sin(self.rad(g)) + 0.020 * math.sin(self.rad(2 * g))
        e = 23.439 - 0.00000036 * D

        RA = (
            self.deg(
                math.atan2(
                    math.cos(self.rad(e)) * math.sin(self.rad(L)), math.cos(self.rad(L))
                )
            )
            / 15
        )
        delta = self.deg(math.asin(math.sin(self.rad(e)) * math.sin(self.rad(L))))
        EqT = q / 15 - RA
        return delta, EqT

    def get_hour_angle(self, altitude, declination):
        try:
            cos_h = (
                math.sin(self.rad(altitude))
                - math.sin(self.rad(self.lat)) * math.sin(self.rad(declination))
            ) / (math.cos(self.rad(self.lat)) * math.cos(self.rad(declination)))
            if cos_h < -1 or cos_h > 1:
                return None
            return self.deg(math.acos(cos_h)) / 15
        except:
            return None

    def get_asr_angle(self, declination):
        shadow_factor = 2 if self.asr_madhab == "HANAFI" else 1
        delta_lat_dec = abs(self.lat - declination)
        altitude = self.deg(
            math.atan(1 / (shadow_factor + math.tan(self.rad(delta_lat_dec))))
        )
        return self.get_hour_angle(altitude, declination)

    def time_diff(self, time1, time2):
        """Returns the difference between two times in hours."""
        if time1 is None or time2 is None:
            return 0
        return (time2 - time1 + 24) % 24

    def resolve_time(
        self, year, month, day, initial_time, base_time, angle, is_fajr=True
    ):
        """
        Applies High Latitude Rules.
        FIX: If NEAREST_LATITUDE is used, we trust the math if it works.
        We only use fallback if the math returns None.
        """
        # 1. Calculate Night Duration
        jd = self.calculate_julian_date(year, month, day)
        dec, _ = self.sun_position(jd)
        ha_sun = self.get_hour_angle(-0.8333, dec)

        if ha_sun is None:
            return None

        night_duration = 2 * ha_sun

        # 2. Define Offset based on Rule
        offset = 0
        if (
            self.high_latitude_rule == "SEVENTH_OF_NIGHT"
            or self.high_latitude_rule == "NEAREST_LATITUDE"
        ):
            offset = night_duration / 7.0
        elif self.high_latitude_rule == "MIDDLE_OF_NIGHT":
            offset = night_duration / 2.0
        elif self.high_latitude_rule == "TWILIGHT_ANGLE":
            offset = (angle / 60.0) * night_duration

        # 3. IF MATH FAILED (None), USE FALLBACK
        if initial_time is None:
            if is_fajr:
                return base_time - offset
            else:
                return base_time + offset

        # 4. IF MATH WORKED (Not None)
        # CRITICAL FIX: If we are mimicking "Nearest Latitude" (Oslo/58.5),
        # we generally TRUST the astronomical calculation of that latitude.
        # We should NOT clamp it with 1/7th unless necessary.
        if self.high_latitude_rule == "NEAREST_LATITUDE":
            return initial_time

        # 5. For other rules (like SEVENTH_OF_NIGHT), apply the Clamp (Sanity Check)
        if is_fajr:
            safe_fajr = base_time - offset
            diff_calc = self.time_diff(initial_time, base_time)
            diff_safe = self.time_diff(safe_fajr, base_time)
            if diff_calc > diff_safe:
                return safe_fajr
            return initial_time
        else:
            safe_isha = base_time + offset
            diff_calc = self.time_diff(base_time, initial_time)
            diff_safe = self.time_diff(base_time, safe_isha)
            if diff_calc > diff_safe:
                return safe_isha
            return initial_time

    # --- Main Logic ---
    def get_times(self, date_obj):
        # Timezone Logic
        if isinstance(self.timezone_input, str):
            tz = ZoneInfo(self.timezone_input)
            offset = tz.utcoffset(date_obj).total_seconds() / 3600
        else:
            offset = self.timezone_input

        # Calc
        jd = self.calculate_julian_date(date_obj.year, date_obj.month, date_obj.day)
        dec, eqt = self.sun_position(jd)
        dhuhr = 12 + offset - (self.lng / 15) - eqt

        # --- Standard Calculation ---
        ha_fajr = self.get_hour_angle(-self.fajr_angle, dec)
        ha_sunrise = self.get_hour_angle(-0.8333, dec)
        ha_maghrib = self.get_hour_angle(-self.maghrib_angle, dec)
        ha_isha = self.get_hour_angle(-self.isha_angle, dec)
        ha_asr = self.get_asr_angle(dec)

        # Handle Polar Day/Night (Sunrise is None)
        if ha_sunrise is None:
            return {
                k: "N/A (Polar)"
                for k in [
                    "Fajr",
                    "Sunrise",
                    "Dhuhr",
                    "Asr",
                    "Maghrib",
                    "Isha",
                    "Imsak",
                    "Midnight",
                ]
            }

        # Base Times (used as anchors)
        sunrise_time = dhuhr - ha_sunrise
        maghrib_time = dhuhr + ha_maghrib  # Sunset (roughly)

        # --- APPLY HIGH LATITUDE FIXES ---

        # 1. Fix Fajr (Anchor: Sunrise)
        raw_fajr = (dhuhr - ha_fajr) if ha_fajr is not None else None
        final_fajr = self.resolve_time(
            date_obj.year,
            date_obj.month,
            date_obj.day,
            raw_fajr,
            sunrise_time,
            self.fajr_angle,
            is_fajr=True,
        )

        # 2. Fix Isha (Anchor: Maghrib/Sunset)
        raw_isha = (dhuhr + ha_isha) if ha_isha is not None else None

        if self.isha_fixed:
            final_isha = maghrib_time + (self.isha_fixed / 60.0)
        else:
            final_isha = self.resolve_time(
                date_obj.year,
                date_obj.month,
                date_obj.day,
                raw_isha,
                maghrib_time,
                self.isha_angle,
                is_fajr=False,
            )

        # 3. Assemble
        times = {
            "Fajr": final_fajr,
            "Sunrise": sunrise_time,
            "Dhuhr": dhuhr,
            "Asr": dhuhr + ha_asr,
            "Maghrib": dhuhr + ha_maghrib,
            "Isha": final_isha,
        }

        # 4. Midnight (Midpoint between Sunset and Fajr)
        # Note: Ideally you calculate Fajr for *tomorrow*, but using today's is acceptable for standard usage
        diff_night = (times["Fajr"] + 24 - times["Maghrib"]) % 24
        times["Midnight"] = (times["Maghrib"] + diff_night / 2) % 24

        times["Imsak"] = times["Fajr"] - (10 / 60.0)

        return {k: self.float_to_time(v) for k, v in times.items()}

    def float_to_time(self, hours):
        if hours is None:
            return "N/A"
        hours = hours % 24
        h = int(hours)
        m = int((hours - h) * 60)
        return f"{h:02d}:{m:02d}"
