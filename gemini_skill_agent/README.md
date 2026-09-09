# Skill AI Agent

An interactive terminal AI Agent powered by **Google Gemini** that understands natural language, answers questions, provides recommendations, executes skills via `skill.md`, accesses private user house tools, and securely logs all multi-component interactions.

---

## 🌟 Key Features

1. **Terminal Interactive Interface**:
   - Continuous interactive loop waiting for natural language input from the terminal (`You: `).
   - Graceful termination on typing `exit`, `quit`, or sending `Ctrl+C` / EOF.

2. **Google Gemini Model Invocation**:
   - Connects directly to Google Gemini models via the official `google-genai` SDK (`gemini-3.6-flash`, with seamless fallback to `gemini-3.5-flash-lite`).
   - Answers general queries, provides insightful recommendations, and handles multi-turn reasoning.

3. **Skill-Driven Architecture (`skill.md`)**:
   - Adheres to the Google Gemini skill specification with YAML frontmatter, clear purpose, and step-by-step procedures.
   - The agent consults `skill.md` to guide the model through extracting city names, determining user intent (weather, local time, or both), and executing the corresponding tools.
   - Weather metrics: temperature (°C), conditions, humidity, and wind speed.
   - Local time metrics: formatted local time, date, IANA timezone, and UTC offset.

4. **Private House Information Tool**:
   - Built-in tool (`get_private_house_information`) capable of securely answering questions about the user's house:
     - **House color**: `blue`
     - **House city location**: `San Jose`
   - Handles individual or combined questions naturally (e.g., *"What is the weather where my house is located?"*).

5. **Comprehensive, Secure Logging (`skill_AI_agent.log`)**:
   - Logs every message exchange between all four core entities:
     - **AI Agent**
     - **LLM** (Google Gemini)
     - **Tools** (`get_weather`, `get_local_time`, `get_private_house_information`)
     - **Skills** (`skill.md`)
   - Includes full request and response payloads.
   - Formatted in clean, indented JSON with visual separators for human readability.
   - Prefixes each interaction session with the required `=== PROMPT ===` line marker.
   - **Security**: Masks all API keys (`GOOGLE_API_KEY`, OpenWeather keys, query parameters) with `[REDACTED_API_KEY]`.

---

## 📁 Project Structure

```text
gemini_skill_agent/
├── skill_AI_Instructions.yaml  # Original specifications & requirements
├── skill.md                    # Gemini model skill definition with frontmatter & procedure
├── skill_AI_agent.py           # Core agent, tool definitions, skill runner & CLI loop
├── skill_AI_agent.log          # Human-readable execution log (API keys masked)
├── .env                        # Environment variables (API keys and model configs)
├── .env.example                # Example environment configuration template
├── .gitignore                  # Git ignore rules for virtualenvs, logs, and secrets
└── README.md                   # Documentation and usage guide
```

---

## 🚀 Setup & Installation

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Google AI Studio API key

### 2. Activate Virtual Environment & Install Dependencies
Activate your virtual environment and install the required packages:
```bash
source .venv/bin/activate
pip install google-genai python-dotenv pyyaml
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` (or update existing `.env`):
```bash
cp .env.example .env
```
Edit `.env` to include your Google API key:
```env
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY="your-gemini-api-key-here"

# Model configuration
MODEL="gemini-3.6-flash"
FALLBACK_MODEL="gemini-3.5-flash-lite"
```

---

## 💻 Running the Agent

Start the interactive agent from your terminal:
```bash
python skill_AI_agent.py
```

### Example Terminal Session

```text
=================================================================
      Skill AI Agent — Powered by Google Gemini       
=================================================================
• Active Skill: city-weather-and-local-time (from skill.md)
• Primary Model: gemini-3.6-flash (Fallback: gemini-3.5-flash-lite)
• Log File: skill_AI_agent.log
-----------------------------------------------------------------
Capabilities:
 1. Ask about city weather (e.g., 'What is the weather in Tokyo?')
 2. Ask about city local time (e.g., 'What time is it in Paris?')
 3. Ask about both (e.g., 'Give me the weather and time in London')
 4. Ask about your house (color / city location)
 5. Ask general questions or request recommendations
Type 'exit' or 'quit' to terminate the session.

You: What is the weather and current local time in Tokyo?

Agent: Here is the current weather and local time for Tokyo, Japan:

### 🕒 Local Time & Date
* Time: 01:42:59 PM
* Date: 2026-09-09
* Timezone: Asia/Tokyo (UTC +09:00)

### 🌤️ Current Weather Conditions
* Temperature: 28°C (Feels like 33°C)
* Condition: Patchy rain nearby
* Humidity: 88%
* Wind Speed: 45 km/h

💡 Recommendation: High humidity and warm temperatures will feel muggy; keep an umbrella handy for patchy rain!

You: What color is my house and where is it located?

Agent: Your house is blue and it is located in San Jose.

You: Can you recommend three great books for learning Python?

Agent: Here are three highly recommended books for learning Python:
1. "Automate the Boring Stuff with Python" by Al Sweigart (Beginner, practical tasks)
2. "Python Crash Course" by Eric Matthes (Hands-on project-based intro)
3. "Fluent Python" by Luciano Ramalho (Idiomatic Python for intermediate/advanced)

You: exit
Goodbye!
```

---

## 🔍 Log File Structure (`skill_AI_agent.log`)

Every prompt entered by the user generates a distinct section in `skill_AI_agent.log`:

```text
=== PROMPT ===
--------------------------------------------------------------------------------
[2026-09-09T04:42:19.864892+00:00] USER -> AGENT (PROMPT)
{
  "query": "What is the weather and current local time in Tokyo?"
}
--------------------------------------------------------------------------------
[2026-09-09T04:42:19.866325+00:00] AGENT -> SKILL (CONSULT_SKILL)
{
  "skill_file": "skill.md",
  "skill_name": "city-weather-and-local-time",
  "user_query": "What is the weather and current local time in Tokyo?"
}
--------------------------------------------------------------------------------
[2026-09-09T04:42:19.866560+00:00] SKILL -> AGENT (SKILL_PROCEDURE_LOADED)
{
  "skill_name": "city-weather-and-local-time",
  "description": "Skill to retrieve current weather information and local time...",
  "procedure": "# City Weather and Local Time Skill\n\n..."
}
--------------------------------------------------------------------------------
[2026-09-09T04:42:19.867443+00:00] AGENT -> LLM (GENERATE_CONTENT_REQUEST)
{
  "iteration": 1,
  "model": "gemini-3.6-flash",
  "system_instruction": "...",
  "tools": [...],
  "contents": [...]
}
--------------------------------------------------------------------------------
[2026-09-09T04:42:58.659005+00:00] LLM -> AGENT (GENERATE_CONTENT_RESPONSE)
{
  "iteration": 1,
  "model": "gemini-3.6-flash",
  "text": null,
  "function_calls": [
    { "name": "get_weather", "args": { "city": "Tokyo" } },
    { "name": "get_local_time", "args": { "city": "Tokyo" } }
  ]
}
--------------------------------------------------------------------------------
[2026-09-09T04:42:58.659213+00:00] SKILL -> TOOL:GET_WEATHER (TOOL_CALL_REQUEST)
{ "arguments": { "city": "Tokyo" } }
--------------------------------------------------------------------------------
[2026-09-09T04:42:59.433712+00:00] TOOL:GET_WEATHER -> SKILL (TOOL_CALL_RESPONSE)
{
  "result": {
    "city": "Tokyo",
    "temperature_c": "28",
    "condition": "Patchy rain nearby",
    "humidity_percent": "88",
    "wind_speed": "45 km/h"
  }
}
--------------------------------------------------------------------------------
[2026-09-09T04:42:59.434497+00:00] SKILL -> TOOL:GET_LOCAL_TIME (TOOL_CALL_REQUEST)
{ "arguments": { "city": "Tokyo" } }
--------------------------------------------------------------------------------
[2026-09-09T04:42:59.435456+00:00] TOOL:GET_LOCAL_TIME -> SKILL (TOOL_CALL_RESPONSE)
{
  "result": {
    "city": "Tokyo",
    "local_time": "01:42:59 PM",
    "local_date": "2026-09-09",
    "timezone": "Asia/Tokyo",
    "utc_offset": "+0900"
  }
}
--------------------------------------------------------------------------------
[2026-09-09T04:42:59.436570+00:00] AGENT -> LLM (GENERATE_CONTENT_REQUEST)
...
--------------------------------------------------------------------------------
[2026-09-09T04:43:00.000000+00:00] AGENT -> USER (FINAL_RESPONSE)
{
  "response": "Here is the current weather and local time for Tokyo, Japan..."
}
--------------------------------------------------------------------------------
```

---

## 🔒 Security

All entries written to `skill_AI_agent.log` pass through a sanitization filter that redacts Google API keys (`AIza...`, `AQ....`), OpenWeather keys, and URL query parameter keys (`key=...`, `appid=...`), ensuring sensitive tokens are never written to disk in plain text.
