---
name: city-weather-and-local-time
description: Skill to retrieve current weather information and local time for any specified city. Use when the user asks about the weather, current conditions, temperature, local time, date, or timezone in a specific city.
---

# City Weather and Local Time Skill

## Description
A skill to help the AI Agent answer questions about current weather conditions and the local time in a specific city.

## When to Use
Activate this skill whenever a user inquiry involves:
- Current weather, temperature, humidity, wind, or weather conditions for a city.
- Current local time, date, or timezone for a city.
- Combined weather and time inquiries for one or more cities.

## Step-by-Step Procedure
The AI Agent must follow these steps when executing this skill:

1. **Identify City**:
   - Extract the target city name from the user's natural language input (e.g., "Paris", "Tokyo", "San Jose").
   - If no city is specified, ask the user to clarify which city they are interested in, or check context (e.g. if the user previously referred to their house location).

2. **Determine Intent**:
   - **Weather query**: Call `get_weather(city=...)`
   - **Local time query**: Call `get_local_time(city=...)`
   - **Both weather & local time**: Call both `get_weather(city=...)` and `get_local_time(city=...)`

3. **Inspect and Verify Tool Outputs**:
   - Verify that the tool response returned valid metrics.
   - If an error occurs (such as city not found or service timeout), provide a polite and informative fallback message without fabricating data.

4. **Formulate Final Response**:
   - Present the information clearly and naturally to the user.
   - For weather: include city name, temperature (°C), current conditions (e.g. Sunny, Overcast, Rain), humidity, and wind speed.
   - For local time: include the formatted local time, date, and timezone.
   - Provide relevant recommendations if appropriate (e.g., bring an umbrella if raining, light clothing if hot).

---

## Tools

### `get_weather`
- **Purpose**: Get current weather metrics for a specified city.
- **Parameters**:
  - `city` (string, required): Name of the target city.
- **Output Schema**:
  - `city` (string): Standardized city name.
  - `temperature_c` (number/string): Current temperature in Celsius.
  - `feels_like_c` (number/string): Feels-like temperature in Celsius.
  - `condition` (string): Human-readable weather description.
  - `humidity_percent` (number/string): Relative humidity percentage.
  - `wind_speed` (string): Current wind speed.

### `get_local_time`
- **Purpose**: Get the current local date, time, and timezone for a specified city.
- **Parameters**:
  - `city` (string, required): Name of the target city.
- **Output Schema**:
  - `city` (string): Standardized city name.
  - `local_time` (string): Formatted local time (e.g., "09:30:15 PM").
  - `local_date` (string): Current local date (YYYY-MM-DD).
  - `timezone` (string): IANA timezone identifier (e.g., "America/Los_Angeles").
  - `utc_offset` (string): UTC offset (e.g., "-0700").
