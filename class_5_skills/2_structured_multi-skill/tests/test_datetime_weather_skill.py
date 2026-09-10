"""Unit tests for datetime-weather-skill routines."""

import pytest
import sys
from pathlib import Path

# Add skill path
SKILL_PATH = Path(__file__).parent.parent / "skills" / "datetime-weather-skill" / "scripts"
if str(SKILL_PATH) not in sys.path:
    sys.path.insert(0, str(SKILL_PATH))

from env_tools import geocode_location, get_weather, get_local_time


def test_geocode_location_valid():
    """Verify geocoding parses valid city coordinates."""
    geo = geocode_location("Tokyo")
    assert geo is not None
    assert "latitude" in geo
    assert "longitude" in geo
    assert isinstance(geo["latitude"], float)
    assert isinstance(geo["longitude"], float)
    assert 34.0 < geo["latitude"] < 37.0


def test_geocode_location_invalid():
    """Verify invalid city raises ValueError."""
    with pytest.raises(ValueError):
        geocode_location("xyz123abcnonexistentcity99999")


def test_get_weather():
    """Verify weather analytics return required metrics without API keys."""
    res = get_weather("London")
    assert res["status"] == "success"
    assert res["city"] == "London"
    assert "temperature_celsius" in res
    assert "condition" in res
    assert "relative_humidity_percent" in res
    assert "wind_speed_kmh" in res


def test_get_local_time():
    """Verify local time and timezone calculation for a known city."""
    res = get_local_time("New York")
    assert res["status"] == "success"
    assert "timezone" in res
    assert "America/New_York" in res["timezone"]
    assert "current_time_12h" in res
    assert "current_date" in res
    assert "formatted_datetime" in res
