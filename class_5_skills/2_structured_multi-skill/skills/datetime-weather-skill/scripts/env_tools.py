"""Public OpenStreetMap Nominatim Geocoding and Open-Meteo Weather & Time logic.

Requires no proprietary API keys.
"""

from datetime import datetime
import json
import logging
from typing import Any, Callable, Dict, Optional
import urllib.parse
from zoneinfo import ZoneInfo
import requests

logger = logging.getLogger(__name__)

# Callback hook for audit logging external API calls
_external_api_logger: Optional[Callable[[str, str, str, str, Dict[str, Any]], None]] = None


def set_external_api_logger(callback: Optional[Callable[[str, str, str, str, Dict[str, Any]], None]]) -> None:
    """Set optional callback to record external API audits.

    Signature: callback(event_type, invoker, target, payload)
    """
    global _external_api_logger
    _external_api_logger = callback


def _record_audit(event_type: str, invoker: str, target: str, payload: Dict[str, Any]) -> None:
    if _external_api_logger:
        try:
            _external_api_logger(event_type, invoker, target, payload)
        except Exception as e:
            logger.debug(f"Audit log callback error: {e}")


WMO_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def geocode_location(city: str) -> Dict[str, Any]:
    """Parse city into exact latitude, longitude, and timezone using OpenStreetMap Nominatim.

    Falls back to Open-Meteo Geocoding if Nominatim is unreachable.
    """
    city_clean = city.strip()
    headers = {
        "User-Agent": "AntigravityMultiSkillAgent/1.0 (agent_eng_labs_user_experiment@domain.org)"
    }
    nominatim_url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(city_clean)}&format=json&limit=1"

    _record_audit("EXTERNAL_API_REQUEST", "datetime-weather-skill", "Nominatim API", {
        "method": "GET",
        "url": nominatim_url,
        "city": city_clean,
        "headers": headers,
    })

    try:
        resp = requests.get(nominatim_url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                first = data[0]
                result = {
                    "city": city_clean,
                    "display_name": first.get("display_name", city_clean),
                    "latitude": float(first["lat"]),
                    "longitude": float(first["lon"]),
                    "source": "OpenStreetMap Nominatim",
                }
                _record_audit("EXTERNAL_API_RESPONSE", "Nominatim API", "datetime-weather-skill", {
                    "status_code": 200,
                    "raw_response": data,
                    "parsed_result": result,
                })
                return result
    except Exception as e:
        logger.warning(f"Nominatim geocoding error for '{city_clean}': {e}. Falling back to Open-Meteo Geocoding.")
        _record_audit("EXTERNAL_API_RESPONSE", "Nominatim API", "datetime-weather-skill", {"error": str(e), "fallback": "Open-Meteo"})

    # Fallback to Open-Meteo geocoding
    open_meteo_geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city_clean)}&count=1&language=en&format=json"
    _record_audit("EXTERNAL_API_REQUEST", "datetime-weather-skill", "Open-Meteo Geocoding API", {
        "method": "GET",
        "url": open_meteo_geo_url,
        "city": city_clean,
    })
    try:
        resp2 = requests.get(open_meteo_geo_url, timeout=8)
        if resp2.status_code == 200:
            data2 = resp2.json()
            results = data2.get("results")
            if results and len(results) > 0:
                first2 = results[0]
                res = {
                    "city": city_clean,
                    "display_name": f"{first2.get('name')}, {first2.get('country', '')}",
                    "latitude": float(first2["latitude"]),
                    "longitude": float(first2["longitude"]),
                    "timezone": first2.get("timezone"),
                    "source": "Open-Meteo Geocoding",
                }
                _record_audit("EXTERNAL_API_RESPONSE", "Open-Meteo Geocoding API", "datetime-weather-skill", {
                    "status_code": 200,
                    "raw_response": data2,
                    "parsed_result": res,
                })
                return res
    except Exception as e:
        logger.error(f"Open-Meteo Geocoding error for '{city_clean}': {e}")
        _record_audit("EXTERNAL_API_RESPONSE", "Open-Meteo Geocoding API", "datetime-weather-skill", {"error": str(e)})

    raise ValueError(f"Could not resolve geocoding coordinates for city: '{city}'")


def get_weather(city: str) -> Dict[str, Any]:
    """Fetch real-time weather analytics for a specified city using Open-Meteo without proprietary API keys.

    Args:
        city: City name (e.g. 'Tokyo', 'San Jose', 'London', 'Paris').

    Returns:
        A dictionary containing real-time weather conditions, temperature, humidity, and wind speed.
    """
    try:
        geo = geocode_location(city)
        lat = geo["latitude"]
        lon = geo["longitude"]

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,"
            f"apparent_temperature,precipitation,weather_code,wind_speed_10m&timezone=auto"
        )

        _record_audit("EXTERNAL_API_REQUEST", "datetime-weather-skill", "Open-Meteo API", {
            "method": "GET",
            "url": weather_url,
            "city": city,
            "latitude": lat,
            "longitude": lon,
        })

        resp = requests.get(weather_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        current = data.get("current", {})
        code = current.get("weather_code", 0)
        condition_desc = WMO_WEATHER_CODES.get(code, "Clear")

        result = {
            "city": city,
            "resolved_location": geo["display_name"],
            "latitude": lat,
            "longitude": lon,
            "timezone": data.get("timezone", "UTC"),
            "temperature_celsius": current.get("temperature_2m"),
            "apparent_temperature_celsius": current.get("apparent_temperature"),
            "relative_humidity_percent": current.get("relative_humidity_2m"),
            "precipitation_mm": current.get("precipitation"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "condition": condition_desc,
            "observation_time": current.get("time"),
            "status": "success",
        }

        _record_audit("EXTERNAL_API_RESPONSE", "Open-Meteo API", "datetime-weather-skill", {
            "status_code": resp.status_code,
            "raw_response": data,
            "parsed_result": result,
        })
        return result
    except Exception as e:
        err_res = {
            "city": city,
            "status": "error",
            "error_message": str(e),
        }
        _record_audit("EXTERNAL_API_RESPONSE", "Open-Meteo API", "datetime-weather-skill", err_res)
        return err_res


def get_local_time(city: str) -> Dict[str, Any]:
    """Get current local date, time, day of week, and timezone for a city.

    Args:
        city: City name (e.g. 'Tokyo', 'San Jose', 'London').

    Returns:
        A dictionary containing the current local time formatted in both 12-hour and 24-hour clocks,
        date, day of week, and resolved timezone.
    """
    try:
        geo = geocode_location(city)
        lat = geo["latitude"]
        lon = geo["longitude"]

        # Query Open-Meteo to get the authoritative timezone for coordinates
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m&timezone=auto"
        _record_audit("EXTERNAL_API_REQUEST", "datetime-weather-skill", "Open-Meteo Timezone API", {
            "method": "GET",
            "url": url,
            "city": city,
            "latitude": lat,
            "longitude": lon,
        })
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        tz_name = data.get("timezone", "UTC")
        now = datetime.now(ZoneInfo(tz_name))

        result = {
            "city": city,
            "resolved_location": geo["display_name"],
            "timezone": tz_name,
            "current_time_12h": now.strftime("%I:%M:%S %p"),
            "current_time_24h": now.strftime("%H:%M:%S"),
            "current_date": now.strftime("%Y-%m-%d"),
            "formatted_datetime": now.strftime("%A, %B %d, %Y, %I:%M %p"),
            "utc_offset": now.strftime("%z"),
            "status": "success",
        }
        _record_audit("EXTERNAL_API_RESPONSE", "Open-Meteo Timezone API", "datetime-weather-skill", {
            "status_code": resp.status_code,
            "raw_response": data,
            "parsed_result": result,
        })
        return result
    except Exception as e:
        err_res = {
            "city": city,
            "status": "error",
            "error_message": str(e),
        }
        _record_audit("EXTERNAL_API_RESPONSE", "Open-Meteo Timezone API", "datetime-weather-skill", err_res)
        return err_res
