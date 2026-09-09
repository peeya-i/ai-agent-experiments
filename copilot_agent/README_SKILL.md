# Gemini Weather and Local Time Skill Agent

`skill_AI_agent.py` is a terminal-based Google Gemini agent that follows the procedure in `skill.md`. It can answer general questions and recommendations, retrieve current weather for a city, retrieve the local time for that city, and answer two private house questions:

- House color: blue
- House city: San Jose

## Setup

1. Activate the project virtual environment:

   ```bash
   source .venv/bin/activate
   ```

2. Install the dependencies if needed:

   ```bash
   pip install google-genai python-dotenv
   ```

3. Create `.env` from `.env.example` and configure the credentials:

   ```dotenv
   GOOGLE_API_KEY=your_google_api_key
   OPENWEATHERMAP_API_KEY=your_openweathermap_api_key
   MODEL=gemini-2.5-flash
   FALLBACK_MODEL=gemini-2.5-flash
   ```

   `OPENWEATHER_API_KEY` may be used instead of `OPENWEATHERMAP_API_KEY`. Keep `.env` private and do not commit API keys.

## Run

From this directory, run:

```bash
python skill_AI_agent.py
```

Enter a natural-language request at the `You:` prompt. Type `quit` or `exit` to stop.

Examples:

```text
You: What is the weather and local time in London?
You: What color is my house?
You: Which city is my house in?
You: Recommend a weekend activity in San Jose.
```

For weather and local-time requests, Gemini uses the tools defined by the skill. Weather is retrieved from OpenWeatherMap and local time is retrieved from WorldTimeAPI. If either service fails, the agent reports the failure instead of inventing data.

## Logging

All interaction records are written to `skill_AI_agent.log`. Each user prompt starts with `=== PROMPT ===`. The log includes readable request and response payloads exchanged among the user, agent, Gemini model, skill tools, and external services. Configured Google and weather-service API keys are redacted before log messages are written.