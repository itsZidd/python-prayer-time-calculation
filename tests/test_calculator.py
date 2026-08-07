# tests/test_calculator.py
"""
Regression suite for AdvancedPrayerCalculator.

Covers:
- The reference cities used to verify the 1.1.0 bug fixes (CHANGELOG.md),
  so any future change that silently reintroduces those bugs gets caught.
- The edge cases found during code review after 1.1.0: invalid
  high_latitude_rule, the TWILIGHT_ANGLE config gap, and genuine polar
  day/night behavior.

Run with: pytest tests/
"""

from datetime import datetime

import pytest

from calculator import AdvancedPrayerCalculator
from config import HIGH_LATITUDE_RULES


# --- Reference cities (pins correct behavior post-1.1.0) ---

def test_jakarta_unaffected_by_high_latitude_fixes():
    """Tropical location — should never touch the high-latitude fallback path at all."""
    calc = AdvancedPrayerCalculator(
        lat=-6.2088, lng=106.8456, timezone="Asia/Jakarta", country="Indonesia"
    )
    times = calc.get_times(datetime(2026, 4, 2))
    assert calc.method_key == "KEMENAG"
    assert times["Fajr"] == "04:37"
    assert times["Dhuhr"] == "11:56"
    assert times["Isha"] == "19:06"


def test_riyadh_unaffected_by_high_latitude_fixes():
    """Subtropical, fixed-minutes Isha method — also should never touch the fallback path."""
    calc = AdvancedPrayerCalculator(
        lat=21.4225, lng=39.8262, timezone="Asia/Riyadh", country="Saudi Arabia"
    )
    times = calc.get_times(datetime(2026, 6, 21))
    assert calc.method_key == "MAKKAH"
    assert times["Fajr"] == "04:11"
    assert times["Dhuhr"] == "12:22"
    assert times["Isha"] == "20:35"


def test_nyc_matches_independent_reference():
    """
    Moderate latitude — this is the case that caught the over-aggressive
    clamp bug. Values verified against an independent published prayer-time
    site (see CHANGELOG.md).
    """
    calc = AdvancedPrayerCalculator(
        lat=40.7128, lng=-74.0060, timezone="America/New_York", country="USA"
    )
    times = calc.get_times(datetime(2026, 7, 30))
    assert times["Fajr"] == "04:20"
    assert times["Sunrise"] == "05:50"
    assert times["Dhuhr"] == "13:02"
    assert times["Asr"] == "16:57"
    assert times["Maghrib"] == "20:14"
    assert times["Isha"] == "21:44"


def test_tromso_no_longer_produces_nonsensical_fajr():
    """
    High latitude, persistent-twilight period (not genuine polar day) — this
    is the case that caught the night_duration bug. Before the fix, Fajr
    landed BEFORE that day's own Maghrib, which is nonsensical.
    """
    calc = AdvancedPrayerCalculator(
        lat=69.6492, lng=18.9553, timezone="Europe/Oslo",
        high_latitude_rule="SEVENTH_OF_NIGHT",
    )
    times = calc.get_times(datetime(2026, 7, 30))
    assert times["Fajr"] == "01:43"
    assert times["Isha"] == "23:58"

    # Sanity invariant: Fajr must always precede Sunrise same-day.
    fajr_h, fajr_m = map(int, times["Fajr"].split(":"))
    sunrise_h, sunrise_m = map(int, times["Sunrise"].split(":"))
    assert (fajr_h, fajr_m) < (sunrise_h, sunrise_m)


def test_tehran_maghrib_angle_resolves_correctly():
    """Shia/Jafari method with a non-default (deeper) maghrib_angle."""
    calc = AdvancedPrayerCalculator(
        lat=35.6892, lng=51.3890, timezone="Asia/Tehran", method="TEHRAN"
    )
    times = calc.get_times(datetime(2026, 7, 30))
    assert times["Fajr"] == "03:32"
    assert times["Dhuhr"] == "12:10"
    assert times["Maghrib"] == "19:31"


# --- Edge cases found in post-1.1.0 review ---

def test_invalid_high_latitude_rule_raises():
    """An unrecognized rule must fail loudly, not silently collapse Fajr->Sunrise / Isha->Maghrib."""
    with pytest.raises(ValueError, match="Unknown high_latitude_rule"):
        AdvancedPrayerCalculator(
            lat=69.6492, lng=18.9553, timezone="Europe/Oslo",
            high_latitude_rule="TYPO_RULE",
        )


@pytest.mark.parametrize("rule", sorted(HIGH_LATITUDE_RULES.keys()))
def test_all_config_rules_are_accepted(rule):
    """Every rule listed in config.HIGH_LATITUDE_RULES must actually be usable — regression guard for the missing-TWILIGHT_ANGLE bug."""
    calc = AdvancedPrayerCalculator(
        lat=69.6492, lng=18.9553, timezone="Europe/Oslo", high_latitude_rule=rule
    )
    times = calc.get_times(datetime(2026, 7, 30))
    assert times["Fajr"] != times["Sunrise"], f"{rule} collapsed Fajr to Sunrise"
    assert times["Isha"] != times["Maghrib"], f"{rule} collapsed Isha to Maghrib"


def test_default_rule_when_none_passed():
    calc = AdvancedPrayerCalculator(
        lat=-6.2088, lng=106.8456, timezone="Asia/Jakarta", country="Indonesia"
    )
    assert calc.high_latitude_rule == "SEVENTH_OF_NIGHT"


# --- Genuine polar day/night behavior (documents CURRENT behavior — see
# the open question in the code review about whether this should change) ---

@pytest.mark.parametrize(
    "rule", ["SEVENTH_OF_NIGHT", "MIDDLE_OF_NIGHT", "TWILIGHT_ANGLE"]
)
def test_genuine_polar_day_returns_na_for_most_rules(rule):
    """
    Longyearbyen, Svalbard (78.2N) in June has genuine midnight sun — the
    sun never sets, so there's no solution even for a plain sunrise/sunset.
    Every rule except NEAREST_LATITUDE currently has no way to produce a
    non-N/A answer here.
    """
    calc = AdvancedPrayerCalculator(
        lat=78.2232, lng=15.6267, timezone="Arctic/Longyearbyen",
        high_latitude_rule=rule,
    )
    times = calc.get_times(datetime(2026, 6, 21))
    assert times["Fajr"] == "N/A (Polar)"


def test_nearest_latitude_handles_polar_coordinates_via_clamping():
    """
    NEAREST_LATITUDE avoids the polar N/A case, but only because it clamps
    self.lat to 58.5 degrees BEFORE any calculation runs — by the time
    get_times() checks for a polar condition, the calculator is no longer
    actually looking at the real (78.2N) latitude at all.
    """
    calc = AdvancedPrayerCalculator(
        lat=78.2232, lng=15.6267, timezone="Arctic/Longyearbyen",
        high_latitude_rule="NEAREST_LATITUDE",
    )
    assert calc.lat == 58.5  # confirms the clamp happened
    times = calc.get_times(datetime(2026, 6, 21))
    assert times["Fajr"] != "N/A (Polar)"


# --- NEAREST_DAY (Aqrab al-Ayyam) ---

def test_nearest_day_still_na_during_genuine_midnight_sun():
    """
    NEAREST_DAY is scoped to persistent-twilight cases (real sunrise/sunset,
    but Fajr/Isha's deeper angle unreachable) — NOT genuine midnight sun,
    where even plain sunrise/sunset has no solution. An earlier version of
    this feature tried extending it to Sunrise/Maghrib too and produced
    inconsistent results (Fajr landing after Sunrise), because Fajr's
    nearest-valid-day search and Sunrise's can land on different days. This
    test pins down the corrected, narrower scope.
    """
    calc = AdvancedPrayerCalculator(
        lat=78.2232, lng=15.6267, timezone="Arctic/Longyearbyen",
        method="MWL", high_latitude_rule="NEAREST_DAY",
    )
    times = calc.get_times(datetime(2026, 6, 21))  # summer solstice — genuine midnight sun here
    assert times["Fajr"] == "N/A (Polar)"


def test_nearest_day_substitutes_during_persistent_twilight():
    """
    Same location, after the genuine-midnight-sun period ends but Fajr/Isha's
    18-degree angle still can't be reached — this is exactly the case
    NEAREST_DAY is meant to handle.
    """
    calc = AdvancedPrayerCalculator(
        lat=78.2232, lng=15.6267, timezone="Arctic/Longyearbyen",
        method="MWL", high_latitude_rule="NEAREST_DAY",
    )
    times = calc.get_times(datetime(2026, 9, 1))
    assert times["Fajr"] != "N/A (Polar)"
    assert times["Sunrise"] != "N/A (Polar)"  # real sunrise still happens here

    # Sanity invariant, same as the Tromso test above.
    fajr_h, fajr_m = map(int, times["Fajr"].split(":"))
    sunrise_h, sunrise_m = map(int, times["Sunrise"].split(":"))
    assert (fajr_h, fajr_m) < (sunrise_h, sunrise_m)


def test_nearest_day_stays_stable_then_resumes_normal_calculation():
    """
    The documented hallmark of Aqrab al-Ayyam: the substituted value stays
    CONSTANT throughout the affected period (reusing the same nearest valid
    day), then automatically returns to real per-day calculation once the
    angle becomes reachable again — no manual toggling required.
    """
    calc = AdvancedPrayerCalculator(
        lat=78.2232, lng=15.6267, timezone="Arctic/Longyearbyen",
        method="MWL", high_latitude_rule="NEAREST_DAY",
    )
    fajr_sep1 = calc.get_times(datetime(2026, 9, 1))["Fajr"]
    fajr_equinox = calc.get_times(datetime(2026, 9, 23))["Fajr"]
    fajr_mid_oct = calc.get_times(datetime(2026, 10, 15))["Fajr"]

    assert fajr_sep1 == fajr_equinox  # stable substitution across the affected period
    assert fajr_mid_oct != fajr_sep1  # resumed real per-day calculation
