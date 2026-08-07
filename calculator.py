# calculator.py
import math
from datetime import datetime, timedelta
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

        # FIX: an unrecognized rule (typo, stale value, etc.) previously fell
        # through every branch in resolve_time()'s offset calculation with no
        # error, silently leaving offset=0 — which collapses Fajr to Sunrise
        # and Isha to Maghrib for any location where the raw calculation has
        # no solution (i.e. exactly the high-latitude cases this is meant to
        # help). Validate eagerly instead of failing silently later.
        if self.high_latitude_rule not in HIGH_LATITUDE_RULES:
            valid = ", ".join(sorted(HIGH_LATITUDE_RULES.keys()))
            raise ValueError(
                f"Unknown high_latitude_rule: {self.high_latitude_rule!r}. "
                f"Valid options are: {valid}"
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
        """
        Converts a standard Gregorian date into a Julian Date (JD).
        Julian dates are a continuous count of days used in astronomy,
        making it much easier to calculate celestial math across different years.
        """
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
        """
        Calculates the Sun's declination and the Equation of Time (EqT).
        - Declination: The angle of the sun relative to the Earth's equator.
        - EqT: The difference between true solar time (sundial) and mean solar time (clock).
        """
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
        """
        Calculates the Hour Angle of the sun for a given altitude.
        This determines how long it takes for the sun to reach a certain angle
        below the horizon (used to find Fajr, Sunrise, Maghrib, and Isha times).
        Returns None if the sun never reaches the specified angle (e.g., polar regions).
        """
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
        """
        Calculates the specific Hour Angle for Asr prayer based on shadow lengths.
        - Standard (Shafi'i/Maliki/Hanbali): Shadow length equals the object's height.
        - Hanafi: Shadow length is twice the object's height.
        """
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

    def find_nearest_valid_time(self, year, month, day, angle_degrees, is_before_noon, tz_offset, max_days=190):
        """
        Aqrab al-Ayyam (Nearest Day): when the sun never reaches
        `angle_degrees` below the horizon on the target date (persistent
        twilight), search outward day-by-day for the closest date — before
        or after — where it IS reachable, and return that day's raw clock
        time (as an hour-of-day float) for reuse on the target date.

        Standard definition (matches the mobile app's implementation of
        this same rule): "use fajr and isha times from the last day when it
        was possible to calculate these times in the normal way."

        Scope note: this is intentionally only ever called for Fajr/Isha.
        It is NOT used for genuine polar day/night (where even plain
        sunrise/sunset has no solution) — see get_times()'s docstring for
        why extending it there produces inconsistent results.
        """
        base = datetime(year, month, day)
        for delta in range(1, max_days + 1):
            for direction in (-1, 1):
                test_date = base + timedelta(days=direction * delta)
                jd = self.calculate_julian_date(test_date.year, test_date.month, test_date.day)
                dec, eqt = self.sun_position(jd)
                dhuhr = 12 + tz_offset - (self.lng / 15) - eqt
                ha = self.get_hour_angle(angle_degrees, dec)
                if ha is not None:
                    return (dhuhr - ha) if is_before_noon else (dhuhr + ha)
        return None  # no valid day found within range — effectively permanent polar conditions

    def resolve_time(
        self, year, month, day, initial_time, base_time, angle, is_fajr=True, tz_offset=0
    ):
        """
        Applies High Latitude Rules.

        FIX #1 (night_duration): `ha_sun` is the hour angle from solar noon to
        sunrise/sunset, so `2 * ha_sun` is the length of DAYLIGHT, not night.
        The original code used this directly as "night_duration", which is
        backwards — corrected below to `24 - (2 * ha_sun)`. This was most
        visible at high latitude in summer (night_duration was computed as
        ~21+ hours when the real night was only ~2-3 hours), but it also
        subtly affected the clamp logic (see Fix #2) at moderate latitudes.

        FIX #2 (over-aggressive clamp): the original code applied a "safety
        clamp" to EVERY valid raw calculation, comparing it against a
        night-fraction boundary and overriding it if the raw value was
        judged "too far" from sunrise/sunset. This was intended only for
        genuine high-latitude edge cases, but it was firing even at
        moderate latitudes (verified: New York, ~40.7°N) where the raw
        15-degree/18-degree sun-angle calculation was already correct and
        didn't need any adjustment. Per PrayTimes.org's own documented
        design intent, these high-latitude fallback rules exist specifically
        for when "the determination of Fajr and Isha is not possible using
        the usual formulas" — i.e. only when the raw calculation has NO
        solution (returns None) — not as a constant sanity-check on a valid
        answer. Fixed: now only used when initial_time is None.

        FEATURE (1.3.0): NEAREST_DAY (Aqrab al-Ayyam) is handled as its own
        branch before the night-duration math below, since it doesn't use
        that math at all — it reuses a nearby day's clock time instead.
        """
        if self.high_latitude_rule == "NEAREST_DAY":
            if initial_time is not None:
                return initial_time
            return self.find_nearest_valid_time(
                year, month, day, -angle, is_fajr, tz_offset
            )

        # 1. Night duration (FIXED: was `2 * ha_sun`, which is daylight length)
        jd = self.calculate_julian_date(year, month, day)
        dec, _ = self.sun_position(jd)
        ha_sun = self.get_hour_angle(-0.8333, dec)

        if ha_sun is None:
            return None

        daylight_duration = 2 * ha_sun
        night_duration = 24 - daylight_duration

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

        # 4. IF MATH WORKED (Not None): trust it directly.
        # FIXED: previously only NEAREST_LATITUDE trusted a valid raw
        # calculation outright; every other rule still ran it through the
        # clamp below even when nothing was wrong with it. Now all rules
        # trust a valid raw calculation, and the fallback offset above is
        # used ONLY when the raw calculation has no solution at all.
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
        sunset_time = dhuhr + ha_sunrise  # physical sunset, used as Maghrib's fallback anchor

        # --- APPLY HIGH LATITUDE FIXES ---

        # Fix Maghrib (FIXED: previously assumed ha_maghrib was always valid
        # whenever ha_sunrise was — methods with a deeper maghrib_angle, e.g.
        # Tehran's Shia-convention 4.5 degrees, can fail independently of
        # plain 0.8333-degree sunset. Previously this silently produced
        # `dhuhr + None`, which Python would raise a TypeError on; now it
        # falls back through resolve_time like Fajr/Isha.)
        if ha_maghrib is not None:
            maghrib_time = dhuhr + ha_maghrib
        else:
            maghrib_time = self.resolve_time(
                date_obj.year,
                date_obj.month,
                date_obj.day,
                None,
                sunset_time,
                self.maghrib_angle,
                is_fajr=False,
                tz_offset=offset,
            )
            if maghrib_time is None:
                maghrib_time = sunset_time

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
            tz_offset=offset,
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
                tz_offset=offset,
            )

        # 3. Assemble
        times = {
            "Fajr": final_fajr,
            "Sunrise": sunrise_time,
            "Dhuhr": dhuhr,
            "Asr": dhuhr + ha_asr,
            "Maghrib": maghrib_time,
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
