# 🕌 Smart Prayer Times API

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A high-precision, offline-capable Prayer Times API built with **Python** and **FastAPI**.

It automatically detects the correct calculation method (e.g., Kemenag for Indonesia, ISNA for USA) and handles complex edge cases like **Arctic/High-Latitude locations** (e.g., Norway) where the sun behaves irregularly.

## ⚡ Features

* **🌍 Smart Auto-Detection:** Automatically detects **Timezone** and **Country** from coordinates.
* **⚙️ Method Mapping:** Automatically assigns the official calculation standard for that country (e.g., Indonesia  Kemenag).
* **❄️ High Latitude Support:** Includes specialized rules (Nearest Latitude/Aqrab Al-Bilad) for locations like Tromsø, Norway.
* **🚀 Lightweight:** Optimized to run on low-memory servers (using `reverse_geocode`).
* **🐳 Docker Ready:** Includes Dockerfile for easy cloud deployment (Render, Fly.io, etc.).

## 🛠️ Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/prayer-times-api.git
cd prayer-times-api

```


2. **Create a virtual environment (Optional but recommended):**
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

```


3. **Install dependencies:**
```bash
pip install -r requirements.txt

```



## 🚀 How to Run

Start the server locally:

```bash
uvicorn api:app --reload

```

The API will be available at: `http://127.0.0.1:8000`

## 📡 API Usage

### Endpoint: `/times`

#### 1. Standard Request (Auto-Detect Everything)

*Best for most of the world (Indonesia, USA, UK, etc).*

```http
GET /times?lat=-7.9689&lng=112.6327

```

**Response:**

```json
{
  "meta": {
    "timezone": "Asia/Jakarta",
    "detected_country": "Indonesia",
    "method_used": "KEMENAG"
  },
  "timings": {
    "Fajr": "04:07",
    "Maghrib": "17:58",
    ...
  }
}

```

#### 2. High-Latitude Request (Arctic/Norway)

*For locations like Tromsø, Norway. Uses the "Nearest Latitude" rule to match local mosque timetables.*

```http
GET /times?lat=69.6492&lng=18.9553&high_latitude_rule=NEAREST_LATITUDE

```

### Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `lat` | float | **Yes** | Latitude (e.g., `-7.98`) |
| `lng` | float | **Yes** | Longitude (e.g., `112.63`) |
| `date` | str | No | Specific date (Format: `YYYY-MM-DD`). Defaults to today. |
| `high_latitude_rule` | str | No | Options: `SEVENTH_OF_NIGHT` (Default) or `NEAREST_LATITUDE` (for Scandinavia). |

## 🐳 Deployment (Docker)

To build and run inside Docker:

```bash
docker build -t prayer-api .
docker run -p 8000:8000 prayer-api

```

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
