# config.py

# --- A. Calculation Methods (Angles & Rules) ---
CALCULATION_METHODS = {
    # 1. Global Standards
    "MWL": {"fajr_angle": 18.0, "isha_angle": 17.0, "name": "Muslim World League"},
    "ISNA": {
        "fajr_angle": 15.0,
        "isha_angle": 15.0,
        "name": "Islamic Society of North America",
    },
    "EGYPT": {
        "fajr_angle": 19.5,
        "isha_angle": 17.5,
        "name": "Egyptian General Authority of Survey",
    },
    # 2. Southeast Asia
    "KEMENAG": {
        "fajr_angle": 20.0,
        "isha_angle": 18.0,
        "name": "Kementerian Agama Indonesia",
    },
    "SINGAPORE": {"fajr_angle": 20.0, "isha_angle": 18.0, "name": "MUIS Singapore"},
    "JAKIM": {
        "fajr_angle": 18.0,
        "isha_angle": 18.0,
        "name": "Jabatan Kemajuan Islam Malaysia",
    },
    # Note: JAKIM sometimes uses 20 for Fajr, but 18 is the standard calculation baseline often cited.
    # 3. Middle East / Gulf
    "MAKKAH": {
        "fajr_angle": 18.5,
        "isha_fixed_minutes": 90,
        "name": "Umm Al-Qura University, Makkah",
    },
    "QATAR": {
        "fajr_angle": 18.0,
        "isha_fixed_minutes": 90,
        "name": "Qatar Calendar House",
    },
    "KUWAIT": {
        "fajr_angle": 18.0,
        "isha_angle": 17.5,
        "name": "Kuwait Ministry of Awqaf",
    },
    "DUBAI": {
        "fajr_angle": 18.2,
        "isha_fixed_minutes": 90,
        "name": "UAE General Authority of Islamic Affairs",
    },
    "TEHRAN": {
        "fajr_angle": 17.7,
        "maghrib_angle": 4.5,
        "isha_angle": 14.0,
        "midnight_method": "JAFARI",
        "name": "University of Tehran (Shia)",
    },
    "TURKEY": {
        "fajr_angle": 18.0,
        "isha_angle": 17.0,
        "name": "Diyanet Isleri Baskanligi",
    },
    # 4. Europe & Russia
    "FRANCE_UOIF": {
        "fajr_angle": 12.0,
        "isha_angle": 12.0,
        "name": "Union of Islamic Organisations of France (UOIF)",
    },
    "FRANCE_15": {
        "fajr_angle": 15.0,
        "isha_angle": 15.0,
        "name": "France (15 degrees)",
    },
    "RUSSIA": {
        "fajr_angle": 16.0,
        "isha_angle": 15.0,
        "name": "Spiritual Administration of Muslims of Russia",
    },
    "LONDON": {
        "fajr_angle": 18.0,
        "isha_angle": 18.0,
        "name": "Unified London Prayer Times",
    },
    # 5. South Asia
    "KARACHI": {
        "fajr_angle": 18.0,
        "isha_angle": 18.0,
        "name": "Univ. of Islamic Sciences, Karachi",
    },
}

# --- B. Country Mapping ---
# This maps the detected country name to the method key above.
COUNTRY_METHOD_MAPPING = {
    # --- Southeast Asia ---
    "indonesia": "KEMENAG",
    "singapore": "SINGAPORE",
    "malaysia": "JAKIM",
    "brunei": "SINGAPORE",
    "thailand": "EGYPT",  # Common fallback
    "philippines": "EGYPT",
    # --- North America ---
    "united states": "ISNA",
    "usa": "ISNA",
    "canada": "ISNA",
    # --- Europe ---
    "united kingdom": "LONDON",
    "uk": "LONDON",
    "great britain": "LONDON",
    "france": "FRANCE_UOIF",  # 12 degrees is very common in France
    "germany": "MWL",  # Germany often follows MWL or Turkey
    "turkey": "TURKEY",
    "russia": "RUSSIA",
    "italy": "MWL",
    "spain": "MWL",
    "netherlands": "MWL",
    "belgium": "MWL",
    # --- Middle East ---
    "saudi arabia": "MAKKAH",
    "uae": "DUBAI",
    "united arab emirates": "DUBAI",
    "dubai": "DUBAI",
    "qatar": "QATAR",
    "kuwait": "KUWAIT",
    "egypt": "EGYPT",
    "iran": "TEHRAN",
    "iraq": "KARACHI",  # Often follows 18/18
    "jordan": "EGYPT",
    "palestine": "EGYPT",
    "lebanon": "EGYPT",
    "oman": "MAKKAH",
    "yemen": "MAKKAH",
    # --- South Asia ---
    "pakistan": "KARACHI",
    "india": "KARACHI",
    "bangladesh": "KARACHI",
    "afghanistan": "KARACHI",
    # --- Africa ---
    "morocco": "MWL",  # Ministry uses 19/17 or 18/17 often
    "algeria": "EGYPT",
    "tunisia": "EGYPT",
    "nigeria": "EGYPT",
    "south africa": "MWL",
}

# C. High Latitude Rules
HIGH_LATITUDE_RULES = {
    # The Safe Defaults
    "SEVENTH_OF_NIGHT": "SEVENTH_OF_NIGHT",
    "MIDDLE_OF_NIGHT": "MIDDLE_OF_NIGHT",
    "NEAREST_LATITUDE": "NEAREST_LATITUDE",
}

DEFAULT_HIGH_LATITUDE_RULE = "SEVENTH_OF_NIGHT"
