---
name: datetime-weather-skill
description: Real-time public weather analytics and local datetime resolution for global locations without requiring proprietary API keys.
keywords:
  - weather
  - forecast
  - temperature
  - climate
  - time
  - current time
  - datetime
  - clock
  - timezone
regex_targets:
  - "(?i)\\b(weather|temperature|forecast|rain|humidity|wind)\\b"
  - "(?i)\\b(time|clock|date|timezone)\\b"
tools:
  - name: get_weather
    description: Fetch real-time weather analytics (temperature, condition, humidity, wind speed) for a specified city using OpenStreetMap Nominatim geocoding and Open-Meteo.
    parameters:
      city:
        type: string
        description: Name of the city or municipality (e.g., 'Tokyo', 'London', 'San Jose').
  - name: get_local_time
    description: Get the current local date, time, and timezone information for a specified city.
    parameters:
      city:
        type: string
        description: Name of the city or municipality (e.g., 'Paris', 'New York', 'Tokyo').
---

# Datetime & Weather Skill

## Standard Operating Procedure (SOP)
1. **Location Parsing**: Extract the explicit or inferred target city from the user query.
2. **Geocoding via OpenStreetMap**: Query Nominatim using an open, identifiable User-Agent to resolve latitude and longitude coordinates. If Nominatim is unavailable, fallback to Open-Meteo Geocoding.
3. **Weather Retrieval via Open-Meteo**: Query Open-Meteo using the resolved coordinates to pull real-time weather parameters (temperature, relative humidity, apparent temperature, precipitation, weather conditions, wind speed).
4. **Local Time Resolution**: Determine the location's official timezone and compute the current local timestamp, 12-hour/24-hour formatted time, and date.
5. **Synthesis**: Return structured, human-readable weather and time analytics to the user.
