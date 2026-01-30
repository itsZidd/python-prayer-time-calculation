# main.py
from datetime import datetime

from calculator import AdvancedPrayerCalculator


def get_user_input():
    print("\n=== Prayer Time Calculator CLI ===")

    # 1. Get Coordinates (with error handling)
    while True:
        try:
            lat_str = input("Enter Latitude (e.g., -6.2088): ")
            lat = float(lat_str)
            lng_str = input("Enter Longitude (e.g., 106.8456): ")
            lng = float(lng_str)
            break
        except ValueError:
            print("Error: Please enter valid numbers for latitude and longitude.")

    # 2. Get Timezone
    # Tip: You can leave this blank to default to 'Asia/Jakarta' if you want,
    # but for now let's make it required.
    print(
        "\n(Common Timezones: Asia/Jakarta, America/New_York, Europe/London, Asia/Riyadh)"
    )
    timezone = input("Enter Timezone ID: ").strip()
    if not timezone:
        timezone = "Asia/Jakarta"  # Default if user hits enter
        print(f"Defaulting to {timezone}...")

    # 3. Get Country (Optional - for auto-method detection)
    country = input(
        "\nEnter Country (e.g., Indonesia, USA) [Optional, press Enter to skip]: "
    ).strip()
    if country == "":
        country = None

    return lat, lng, timezone, country


if __name__ == "__main__":
    # 1. Get inputs from terminal
    lat, lng, tz, country = get_user_input()

    # 2. Initialize Calculator
    try:
        calc = AdvancedPrayerCalculator(lat=lat, lng=lng, timezone=tz, country=country)

        # 3. Calculate
        now = datetime.now()
        times = calc.get_times(now)

        # 4. Display Results
        print(f"\n--- Prayer Times for {now.date()} ---")
        print(f"Location: {lat}, {lng}")
        print(f"Method Used: {calc.method_key}")
        print("-" * 30)

        for prayer, time in times.items():
            print(f"{prayer:<10}: {time}")

        print("-" * 30)

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print(
            "Double check your Timezone ID (it must be a valid IANA string like 'Asia/Jakarta')."
        )
