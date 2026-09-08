# City Weather and Local Time Skill (Skill 2)

## Name
`city_weather_and_local_time`

## Description
A modular skill designed for Google Gemini agents to answer natural language inquiries regarding current weather conditions and accurate local time in any specified city worldwide.

## Procedure
1. **Identify City and Query Intent**:
   - Extract the city name mentioned by the user.
   - Detect whether the user is asking for:
     - Weather information
     - Current local time
     - Both weather and local time
2. **Execute Required Tools**:
   - For weather queries: Invoke the `get_weather` tool with `city=<city_name>`.
   - For local time queries: Invoke the `get_local_time` tool with `city=<city_name>`.
   - For dual queries: Invoke both `get_weather` and `get_local_time`.
3. **Validate and Format Results**:
   - Read the tool response dictionary.
   - For weather, report the temperature in Celsius, conditions, humidity, and wind speed.
   - For local time, report the formatted current time, current date, timezone, and UTC offset.
4. **Fallback & Error Handling**:
   - If a tool fails to retrieve details for an unknown city or due to network error, clearly inform the user without fabricating data.

## Tools

### get_weather
- **Description**: Retrieves current weather observations (temperature, condition, humidity, wind) for a specified city.
- **Parameters**:
  - `city` (string, required): The target city name (e.g. "Paris", "San Jose", "Tokyo").
- **Returns**:
  - `city`: Name of the city
  - `temperature_c`: Temperature in Celsius
  - `feels_like_c`: Apparent temperature in Celsius
  - `condition`: Summary condition description (e.g., "Clear", "Overcast", "Rain")
  - `humidity_percent`: Humidity percentage
  - `wind_speed`: Wind speed with units

### get_local_time
- **Description**: Retrieves current local time, local date, and timezone details for a specified city.
- **Parameters**:
  - `city` (string, required): The target city name (e.g. "Tokyo", "Rio de Janeiro", "London").
- **Returns**:
  - `city`: Name of the city
  - `local_time`: Formatted 12-hour time with AM/PM (e.g., "07:30:00 PM")
  - `local_date`: ISO format date (YYYY-MM-DD)
  - `timezone`: IANA timezone name (e.g., "America/Sao_Paulo")
  - `utc_offset`: Standard UTC offset (e.g., "-0300")
