"""Tools for Skill 1: City Weather and Local Time.

Contains the python implementations of the tools for skill_1:
- get_weather: Retrieves current weather for a city
- get_local_time: Retrieves current local time and timezone for a city
"""

from __future__ import annotations

import datetime
import json
import os
import urllib.parse
import urllib.request
import zoneinfo
from typing import Any

# Logger callback mechanism for recording tool events
_logger_callback = None


def set_logger(callback: Any) -> None:
    """Register logger callback function for tool event tracking."""
    global _logger_callback
    _logger_callback = callback


def log_event(sender: str, recipient: str, message_type: str, payload: Any = None) -> None:
    """Forward event to registered logger callback or logging.py if available."""
    if _logger_callback is not None:
        try:
            _logger_callback(sender, recipient, message_type, payload)
            return
        except Exception:
            pass
    try:
        import logging as _log_module
        if hasattr(_log_module, "log_event"):
            _log_module.log_event(sender, recipient, message_type, payload)
    except Exception:
        pass

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

CITY_TIMEZONES: dict[str, str] = {
    "san jose": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "los angeles": "America/Los_Angeles",
    "seattle": "America/Los_Angeles",
    "new york": "America/New_York",
    "boston": "America/New_York",
    "chicago": "America/Chicago",
    "austin": "America/Chicago",
    "denver": "America/Denver",
    "london": "Europe/London",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "madrid": "Europe/Madrid",
    "rome": "Europe/Rome",
    "amsterdam": "Europe/Amsterdam",
    "tokyo": "Asia/Tokyo",
    "kyoto": "Asia/Tokyo",
    "beijing": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong",
    "singapore": "Asia/Singapore",
    "seoul": "Asia/Seoul",
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "dubai": "Asia/Dubai",
    "mumbai": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "bangalore": "Asia/Kolkata",
    "rio de janeiro": "America/Sao_Paulo",
    "sao paulo": "America/Sao_Paulo",
    "cairo": "Africa/Cairo",
    "toronto": "America/Toronto",
    "vancouver": "America/Vancouver",
}


def get_weather(city: str) -> dict[str, Any]:
    """Retrieve current weather observation for a specified city (temperature, condition, humidity, wind)."""
    log_event("agent", "skill_1:weather", "tool_request", {"city": city})
    clean_city = city.strip()
    encoded_city = urllib.parse.quote(clean_city)

    # 1. OpenWeatherMap if configured
    if OPENWEATHER_API_KEY:
        owm_url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={encoded_city}&appid={OPENWEATHER_API_KEY}&units=metric"
        )
        log_event("skill_1:weather", "external_service", "openweather_request", {"url": owm_url, "city": clean_city})
        try:
            req = urllib.request.Request(owm_url, headers={"User-Agent": "skill_1_agent/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            log_event("external_service", "skill_1:weather", "openweather_response", data)
            result = {
                "city": data.get("name", clean_city),
                "temperature_c": data.get("main", {}).get("temp"),
                "feels_like_c": data.get("main", {}).get("feels_like"),
                "condition": (data.get("weather") or [{}])[0].get("description", "Unknown"),
                "humidity_percent": data.get("main", {}).get("humidity"),
                "wind_speed": f"{data.get('wind', {}).get('speed', 'N/A')} m/s",
            }
            log_event("skill_1:weather", "agent", "tool_response", result)
            return result
        except Exception as err:
            log_event("skill_1:weather", "agent", "openweather_fallback", {"error": str(err)})

    # 2. wttr.in fallback (free, no API key required)
    wttr_url = f"https://wttr.in/{encoded_city}?format=j1"
    log_event("skill_1:weather", "external_service", "wttr_request", {"url": wttr_url, "city": clean_city})
    try:
        req = urllib.request.Request(wttr_url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        log_event("external_service", "skill_1:weather", "wttr_response", {"status": "success"})
        curr = data["current_condition"][0]
        desc = curr.get("weatherDesc", [{}])[0].get("value", "Clear")
        result = {
            "city": clean_city.title(),
            "temperature_c": curr.get("temp_C"),
            "feels_like_c": curr.get("FeelsLikeC"),
            "condition": desc,
            "humidity_percent": curr.get("humidity"),
            "wind_speed": f"{curr.get('windspeedKmph')} km/h",
        }
        log_event("skill_1:weather", "agent", "tool_response", result)
        return result
    except Exception as err:
        log_event("external_service", "skill_1:weather", "weather_error", {"error": str(err)})
        err_res = {"error": f"Unable to fetch weather information for '{clean_city}': {err}"}
        log_event("skill_1:weather", "agent", "tool_response", err_res)
        return err_res


def get_local_time(city: str) -> dict[str, Any]:
    """Retrieve current local time, date, and timezone for a specified city."""
    log_event("agent", "skill_1:local_time", "tool_request", {"city": city})
    clean_city = city.strip().lower()

    tz_name = CITY_TIMEZONES.get(clean_city)
    if not tz_name:
        for known_city, known_tz in CITY_TIMEZONES.items():
            if known_city in clean_city or clean_city in known_city:
                tz_name = known_tz
                break

    if tz_name:
        try:
            tz = zoneinfo.ZoneInfo(tz_name)
            now = datetime.datetime.now(tz)
            result = {
                "city": city.strip().title(),
                "local_time": now.strftime("%I:%M:%S %p"),
                "local_date": now.strftime("%Y-%m-%d"),
                "timezone": tz_name,
                "utc_offset": now.strftime("%z"),
            }
            log_event("skill_1:local_time", "agent", "tool_response", result)
            return result
        except Exception as err:
            log_event("skill_1:local_time", "agent", "timezone_error", {"error": str(err)})

    # Fallback to WorldTimeAPI
    wta_url = f"https://worldtimeapi.org/api/timezone/{urllib.parse.quote(tz_name or clean_city)}"
    log_event("skill_1:local_time", "external_service", "worldtime_request", {"url": wta_url})
    try:
        req = urllib.request.Request(wta_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        log_event("external_service", "skill_1:local_time", "worldtime_response", data)
        result = {
            "city": city.strip().title(),
            "local_time": data.get("datetime", "")[11:19],
            "local_date": data.get("datetime", "")[:10],
            "timezone": data.get("timezone"),
            "utc_offset": data.get("utc_offset"),
        }
        log_event("skill_1:local_time", "agent", "tool_response", result)
        return result
    except Exception as err:
        log_event("external_service", "skill_1:local_time", "time_error", {"error": str(err)})
        err_res = {"error": f"No timezone information available for city '{city}'."}
        log_event("skill_1:local_time", "agent", "tool_response", err_res)
        return err_res
