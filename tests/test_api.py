# tests/test_api.py
"""
Tests for the /times endpoint's city-search feature (api.py), covering:
- Resolving a plain city name to coordinates.
- Disambiguating cities that share a name via the optional `country` param,
  and the most-populous-match default when no country is given.
- Error handling: unknown city (404), neither city nor lat/lng given (422).
- That coordinate-based queries still work unchanged.

Run with: pytest tests/
"""

from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


def test_city_resolves_to_coordinates():
    r = client.get("/times", params={"city": "Jakarta", "year": 2026, "month": 4, "day": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["city"]["name"] == "Jakarta"
    assert body["meta"]["city"]["country_code"] == "ID"
    assert body["meta"]["country"] == "Indonesia"
    assert body["timings"]["Fajr"] == "04:37"


def test_ambiguous_city_defaults_to_most_populous():
    """'Paris' matches both Paris, France (pop ~2.1M) and Paris, Texas (pop ~25k)."""
    r = client.get("/times", params={"city": "Paris"})
    assert r.status_code == 200
    assert r.json()["meta"]["city"]["country_code"] == "FR"


def test_ambiguous_city_disambiguated_by_country():
    r = client.get("/times", params={"city": "Paris", "country": "US"})
    assert r.status_code == 200
    assert r.json()["meta"]["city"]["country_code"] == "US"


def test_unknown_city_returns_404():
    r = client.get("/times", params={"city": "Nonexistentcityxyz123"})
    assert r.status_code == 404


def test_neither_city_nor_coordinates_returns_422():
    r = client.get("/times")
    assert r.status_code == 422


def test_coordinates_still_work_without_city():
    r = client.get("/times", params={"lat": -6.2088, "lng": 106.8456})
    assert r.status_code == 200
    assert r.json()["meta"]["city"] is None


def test_city_takes_precedence_over_conflicting_coordinates():
    """If both are given, `city` wins — documented behavior, not undefined."""
    r = client.get("/times", params={"city": "Jakarta", "lat": 0, "lng": 0})
    assert r.status_code == 200
    assert r.json()["meta"]["city"]["name"] == "Jakarta"
    assert r.json()["meta"]["latitude"] != 0
