# skill.md

## Skill: Weather and Local Time Lookup

**Purpose**: Enable the AI agent to answer questions about the current weather and local time for a specified city.

**Input**: A natural‑language query mentioning a city and requesting either weather information or local time.

**Procedure**:
1. Extract the city name from the query.
2. Determine whether the user wants weather or time.
3. Call the appropriate tool:
   - `get_weather(city)` – fetches weather data from OpenWeatherMap.
   - `get_local_time(city)` – fetches current time from the World Time API.
4. Return a concise, human‑readable answer.

**Tool definitions** (to be implemented in `skill_AI_agent.py`):
- `def get_weather(city: str) -> str:`
  - Uses the `OPENWEATHER_API_KEY` environment variable and the OpenWeatherMap API.
  - Returns a sentence like "In Paris it is 12 °C with clear skies."
- `def get_local_time(city: str) -> str:`
  - Calls the World Time API (no API key required) to obtain the current datetime for the city's timezone.
  - Returns a sentence like "The current time in Tokyo is 03:45 PM (JST)."

**Error handling**:
- If the city cannot be resolved, respond with "I couldn't find information for *{city}*."
- If an API request fails, return a generic error message.

**Logging**: All tool calls must be logged via the `_log_tool` helper (same format as the main AI agent).

**Example usage**:
```
User: What's the weather in London?
Agent: In London, it is 8 °C with light rain.

User: What time is it in New York?
Agent: The current time in New York is 09:15 AM (EDT).
```
