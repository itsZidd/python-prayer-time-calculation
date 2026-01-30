# Smart Prayer Times API & CLI

## 📖 Overview
This project calculates Islamic prayer times based on latitude, longitude, and timezone. It includes advanced handling for high-latitude locations (like Norway or Sweden) and automatically detects the best calculation method (MWL, ISNA, KEMENAG, etc.) based on the country's coordinates.

## 🗂️ Project Structure
* **`api.py`**: The FastAPI web server. Handles HTTP requests, auto-detects timezones, and reverse-geocodes coordinates to countries.
* **`calculator.py`**: The core math engine. Calculates Julian dates, solar declination, hour angles, and applies high-latitude fallback rules.
* **`config.py`**: Contains all calculation constants. Maps specific angles for Fajr/Isha and links countries to their default local standards.
* **`main.py`**: A Command Line Interface (CLI) to run calculations directly in your terminal.

## 🚀 How to Run

### 1. Run the Web API
Install the required libraries, then start the server:
`pip install -r requirements.txt`
`uvicorn api:app --reload`

Once running, open your browser and go to **`http://localhost:8000/docs`** to see the interactive API documentation.

### 2. Run the Terminal CLI
To test coordinates quickly in your terminal without starting the server:
`python main.py`
Follow the prompts to enter your latitude, longitude, and timezone.

## 📡 API Response Example
When you make a GET request to `/times` with coordinates, the API returns a structured JSON response containing the metadata and the calculated prayer times.

**Example Request:**
`GET http://localhost:8000/times?lat=-6.2088&lng=106.8456`

**Example Response:**
```json
{
  "meta": {
    "date": "2026-04-02",
    "latitude": -6.2088,
    "longitude": 106.8456,
    "timezone": "Asia/Jakarta",
    "country": "Indonesia",
    "method_used": "KEMENAG",
    "high_lat_rule": "SEVENTH_OF_NIGHT"
  },
  "timings": {
    "Fajr": "04:40",
    "Sunrise": "05:52",
    "Dhuhr": "11:58",
    "Asr": "15:15",
    "Maghrib": "18:00",
    "Isha": "19:08",
    "Midnight": "23:20",
    "Imsak": "04:30"
  }
}
