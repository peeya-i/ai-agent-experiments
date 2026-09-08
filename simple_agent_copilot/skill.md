# City Weather and Local Time Skill

## Name

`city_weather_and_local_time`

## Purpose

Help the agent answer questions about current weather and local time for a specific city.

## Procedure

1. Identify the city in the user's request.
2. Call `get_weather` to retrieve current weather from OpenWeatherMap.
3. Call `get_local_time` to retrieve the city's local time from WorldTimeAPI.
4. Present the returned weather and time clearly, naming the city.
5. If a service fails, report the failure and do not invent data.

## Tools

### get_weather

Input:

```json
{"city": "string"}
```

Returns current temperature, conditions, humidity, wind, and location details.

### get_local_time

Input:

```json
{"city": "string"}
```

Returns the city's IANA timezone, local date/time, and UTC offset.
