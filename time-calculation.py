import math
from datetime import datetime, timedelta


class PrayerTimeCalculator:
    def __init__(
        self,
        lat,
        lng,
        timezone,
        angle_fajr=18.0,
        angle_isha=18.0,
        asr_method="STANDARD",
    ):
        self.lat = lat
        self.lng = lng
        self.timezone = timezone  # e.g., 7 for WIB (UTC+7)
        self.fajr_angle = angle_fajr
        self.isha_angle = angle_isha
        self.asr_method = asr_method  # STANDARD (Shafi/Maliki/Hanbali) or HANAFI

    # --- Helper Math Functions ---
    def rad(self, d):
        return math.radians(d)

    def deg(self, r):
        return math.degrees(r)

    # --- Astronomical Calculations ---

    def calculate_julian_date(self, year, month, day):
        # Algorithm to convert Gregorian date to Julian Date
        if month <= 2:
            year -= 1
            month += 12

        a = math.floor(year / 100)
        b = 2 - a + math.floor(a / 4)

        jd = (
            math.floor(365.25 * (year + 4716))
            + math.floor(30.6001 * (month + 1))
            + day
            + b
            - 1524.5
        )
        return jd

    def sun_position(self, jd):
        # Calculate Sun's position using low-precision formulas (sufficient for prayer times)
        D = jd - 2451545.0
        g = 357.529 + 0.98560028 * D
        q = 280.459 + 0.98564736 * D
        L = q + 1.915 * math.sin(self.rad(g)) + 0.020 * math.sin(self.rad(2 * g))

        R = (
            1.00014
            - 0.01671 * math.cos(self.rad(g))
            - 0.00014 * math.cos(self.rad(2 * g))
        )
        e = 23.439 - 0.00000036 * D

        RA = (
            self.deg(
                math.atan2(
                    math.cos(self.rad(e)) * math.sin(self.rad(L)), math.cos(self.rad(L))
                )
            )
            / 15
        )

        # Declination of the Sun
        delta = self.deg(math.asin(math.sin(self.rad(e)) * math.sin(self.rad(L))))

        # Equation of Time
        EqT = q / 15 - RA
        return delta, EqT

    # --- Prayer Time Logic ---

    def calculate_times(self, year, month, day):
        jd = self.calculate_julian_date(year, month, day)
        dec, eqt = self.sun_position(jd)

        # 1. Dhuhr: When sun is at meridian (Noon)
        # Formula: 12 + Timezone - Longitude/15 - EquationOfTime
        dhuhr = 12 + self.timezone - (self.lng / 15) - eqt

        # 2. Sun Altitude Angles for specific times
        # Horizon correction is usually 0.8333 degrees due to refraction
        horizon_correction = 0.8333

        # Calculate Hour Angles
        ha_fajr = self.get_hour_angle(-self.fajr_angle, dec)
        ha_sunrise = self.get_hour_angle(-horizon_correction, dec)
        ha_maghrib = self.get_hour_angle(-horizon_correction, dec)
        ha_isha = self.get_hour_angle(-self.isha_angle, dec)

        # Calculate Asr Hour Angle specifically
        ha_asr = self.get_asr_hour_angle(dec)

        # Apply offsets from Dhuhr
        # Fajr/Sunrise are BEFORE noon (subtract time)
        # Asr/Maghrib/Isha are AFTER noon (add time)

        times = {
            "Fajr": dhuhr - ha_fajr,
            "Sunrise": dhuhr - ha_sunrise,
            "Dhuhr": dhuhr,
            "Asr": dhuhr + ha_asr,
            "Maghrib": dhuhr + ha_maghrib,
            "Isha": dhuhr + ha_isha,
        }

        return {k: self.float_to_time(v) for k, v in times.items()}

    def get_hour_angle(self, altitude, declination):
        # Solves cos(H) = (sin(altitude) - sin(lat)*sin(dec)) / (cos(lat)*cos(dec))
        cos_h = (
            math.sin(self.rad(altitude))
            - math.sin(self.rad(self.lat)) * math.sin(self.rad(declination))
        ) / (math.cos(self.rad(self.lat)) * math.cos(self.rad(declination)))

        # Clamp value between -1 and 1 to avoid math errors
        cos_h = max(-1, min(1, cos_h))

        angle = self.deg(math.acos(cos_h))
        return angle / 15  # Convert degrees to hours

    def get_asr_hour_angle(self, declination):
        # Asr Shadow Ratio: 1 (Standard) or 2 (Hanafi)
        shadow_length = 2 if self.asr_method == "HANAFI" else 1

        # Kotan(A) = ShadowLength + tan(Abs(Lat - Declination))
        delta_lat_dec = abs(self.lat - declination)
        altitude_asr = self.deg(
            math.atan(1 / (shadow_length + math.tan(self.rad(delta_lat_dec))))
        )

        return self.get_hour_angle(altitude_asr, declination)

    def float_to_time(self, hours):
        # Convert decimal hours (e.g., 12.5) to "12:30" string
        hours = hours % 24  # Normalize to 24h
        h = int(hours)
        m = int((hours - h) * 60)
        s = int((((hours - h) * 60) - m) * 60)
        return f"{h:02d}:{m:02d}:{s:02d}"


# --- Usage Example ---

# Coordinates for Jakarta, Indonesia
lat = -6.2088
lng = 106.8456
tz = 7  # UTC+7

# Standard angles (MWL uses 18 degrees for Fajr/Isha usually, though Indonesia Kemenag uses 20/18)
# Let's use 20 for Fajr and 18 for Isha (typical Indonesia)
calc = PrayerTimeCalculator(lat, lng, tz, angle_fajr=20.0, angle_isha=18.0)

now = datetime.now()
prayer_times = calc.calculate_times(now.year, now.month, now.day)

print(f"Prayer Times for {now.date()}:")
for name, time in prayer_times.items():
    print(f"{name}: {time}")
