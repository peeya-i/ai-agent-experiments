---
name: city_weather_and_local_time
description: >-
  Use this skill when the user asks about the weather in a specific city,
  the local time in that city, or both. Activates the weather and local time
  lookup workflow to fetch current weather conditions and accurate time.
---

# City Weather and Local Time Skill (Skill 1)

## Name
`city_weather_and_local_time`

## Description
A modular Gemini skill that enables the AI Agent to accurately answer user questions
regarding current weather conditions (temperature, sky condition, humidity, wind speed)
and local time/timezone for any specified city worldwide.

## Procedure
1. **Identify City**: Extract the target city name from the user's natural language request.
2. **Determine Query Intent**:
   - If the user asks about weather: Invoke `get_weather(city=...)`.
   - If the user asks about local time: Invoke `get_local_time(city=...)`.
   - If the user asks about both (or requests weather and time): Invoke both `get_weather` and `get_local_time`.
3. **Execute Tools**:
   - The Python code for the tools is in the same folder (`tools.py`).
4. **Format Response**:
   - Present the temperature in Celsius, weather conditions, humidity, and wind speed.
   - Present the current local time (12-hour format with AM/PM), local date, timezone, and UTC offset.
5. **Error Handling**:
   - If the city is unrecognized or the service is temporarily unreachable, inform the user honestly without fabricating data.

## Tools

### get_weather
- **Purpose**: Retrieve current weather observations for a specified city.
- **Parameters**:
  - `city` (string, required): The target city name (e.g. "San Jose", "Tokyo", "London", "Paris").
- **Returns**:
  - `city`: Name of the city
  - `temperature_c`: Current temperature in Celsius
  - `feels_like_c`: Apparent temperature in Celsius
  - `condition`: Weather description (e.g., "Clear", "Overcast", "Light rain")
  - `humidity_percent`: Relative humidity percentage
  - `wind_speed`: Wind speed with units

### get_local_time
- **Purpose**: Retrieve the current local time, date, and timezone for a specified city.
- **Parameters**:
  - `city` (string, required): The target city name (e.g. "San Jose", "Tokyo", "New York", "Berlin").
- **Returns**:
  - `city`: Name of the city
  - `local_time`: Formatted 12-hour local time (e.g., "02:30:00 PM")
  - `local_date`: ISO date string (YYYY-MM-DD)
  - `timezone`: IANA timezone name (e.g., "America/Los_Angeles")
  - `utc_offset`: Standard UTC offset (e.g., "-0700")

## Example Questions
- "What is the weather in Paris?"
- "What time is it in Tokyo?"
- "Can you check the weather and local time in London?"
- "What is the weather in the city where my house is located?"
