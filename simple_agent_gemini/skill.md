# City Weather and Local Time Skill

## Name
`city_weather_and_local_time`

## Description
A skill to help the AI Agent answer questions about current weather conditions and the local time in a specific city.

## Procedure
1. **Identify City**: Extract the target city name from the user's request.
2. **Determine Intent**:
   - If the user asks about the weather, invoke `get_weather(city=...)`.
   - If the user asks about the current local time, invoke `get_local_time(city=...)`.
   - If the user asks for both weather and time (e.g., "what's the weather and time in Paris?"), invoke both tools.
3. **Inspect Output**: Review the structured output returned by the tool(s).
4. **Formulate Response**: Provide a clear, natural, and helpful response incorporating the retrieved data (e.g., temperature, conditions, local time, timezone).
5. **Handle Errors**: If a tool reports that data could not be found or a service is unavailable, inform the user honestly without inventing unverified information.

## Tools

### get_weather
- **Purpose**: Get current weather metrics for a specified city.
- **Input Parameters**:
  - `city` (string, required): Name of the city (e.g., "San Jose", "Tokyo", "London").
- **Output Schema**:
  - `city`: City name
  - `temperature_c`: Temperature in Celsius
  - `condition`: Weather description (e.g., "Clear", "Partly cloudy", "Rain")
  - `humidity_percent`: Relative humidity percentage
  - `wind_speed`: Wind speed details

### get_local_time
- **Purpose**: Get the current local date, time, and timezone for a specified city.
- **Input Parameters**:
  - `city` (string, required): Name of the city (e.g., "San Jose", "New York", "Berlin").
- **Output Schema**:
  - `city`: City name
  - `local_time`: Formatted current local time (e.g., "02:30 PM")
  - `local_date`: Formatted current local date (e.g., "2026-09-08")
  - `timezone`: IANA timezone identifier (e.g., "America/Los_Angeles")
  - `utc_offset`: UTC offset (e.g., "-07:00")
