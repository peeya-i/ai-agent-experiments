# Structured Multi-Skill AI Agent

An autonomous, multi-skill AI agent application built with the official **Google GenAI SDK** (`google-genai`). The system architecture isolates domain-specific procedural logic and flat-file assets into structured skill directories, enforces strict anti-hallucination policies, logs all events asynchronously in redacted JSON format, and provides an interactive 2-page web interface (Chat & Log Review).

---

## 📂 Architecture & Directory Layout

```
antigravity-agent/
├── app.py                             # FastAPI Web Application & API orchestrator
├── agent.py                           # Core Orchestrator utilizing google-genai SDK
├── logging.py                         # Asynchronous JSON audit logger with API key redaction
├── requirements.txt                   # Package dependencies
├── .env                               # Google AI Studio API key and model configurations
├── logs/
│   └── agent_audit.jsonl              # Asynchronous persistent JSON audit logs
├── static/
│   ├── index.html                     # 2-Page Web UI (Chat with Agent & Log Review)
│   ├── style.css                      # Modern glassmorphic dark-theme styling
│   └── app.js                         # Dynamic page switcher, chat flow & JSON modal inspector
├── skills/
│   ├── datetime-weather-skill/
│   │   ├── SKILL.md                   # Control manifest (YAML frontmatter & SOP)
│   │   └── scripts/
│   │       ├── __init__.py
│   │       └── env_tools.py           # Nominatim geocoding + Open-Meteo weather & time (No Keys Req.)
│   ├── house-registry-skill/
│   │   ├── SKILL.md                   # Control manifest (YAML frontmatter & Anti-Hallucination SOP)
│   │   ├── data/
│   │   │   └── registry.csv           # Flat-file database for record resolution
│   │   └── scripts/
│   │       ├── __init__.py
│   │       └── registry_tools.py      # Strict case-insensitive containment scanner
│   └── plant-care-skill/
│       ├── SKILL.md                   # Control manifest (YAML frontmatter & Horticultural SOP)
│       ├── templates/
│       │   └── plant_info.md          # Comprehensive plant care instructions template
│       └── scripts/
│           ├── __init__.py
│           └── plant_tools.py         # Botanical profiles & care guide formatting
└── tests/
    ├── conftest.py                    # Pytest environment bootstrap
    ├── test_datetime_weather_skill.py # Unit tests for weather, geocoding & time
    ├── test_house_registry_skill.py   # Unit tests for registry containment lookup
    ├── test_plant_care_skill.py       # Unit tests for plant care guides & template
    ├── test_logging.py                # Unit tests for async JSON logging & redaction
    ├── test_agent.py                  # Unit tests for GenAI client & tool execution
    └── test_integration.py            # End-to-end API and UI integration tests
```

---

## 🚀 Capabilities & Features

### 1. Skill 1: `datetime-weather-skill`
- **Geocoding Engine (`geocode_location`)**: Queries OpenStreetMap Nominatim with open user agent strings to resolve global city names into exact latitude and longitude boundaries, with fallback to Open-Meteo geocoding.
- **Weather Analytics (`get_weather`)**: Queries Open-Meteo forecast API for current temperature (°C), apparent temperature, humidity, precipitation, wind speed, and weather condition without requiring proprietary API keys.
- **Local Time Resolution (`get_local_time`)**: Computes authoritative local time, 12-hour/24-hour clocks, date, and timezone for any city worldwide.

### 2. Skill 2: `house-registry-skill`
- **Flat-File Database (`registry.csv`)**: Tabular database tracking `name,city,country,house_color`.
- **Anti-Hallucination SOP (`lookup_house_record`)**: Enforces strict, case-insensitive containment scanning over verified static database records. If a record is not found, the agent explicitly states so rather than hallucinating details.
- **Full Discovery (`list_registry_records`)**: Allows retrieving verified resident assets.

### 3. Skill 3: `plant-care-skill`
- **Comprehensive Care Template (`plant_info.md`)**: Horticultural template covering scientific taxonomy, soil composition & pH, light tolerances, watering routines, temperature & humidity, routine maintenance, propagation, common pests/diseases, and safety/toxicity.
- **Dynamic Care Guide Generator (`get_plant_care_instructions`)**: Provides formatted, plant-specific care guides for popular houseplants (Monstera, Snake Plant, Fiddle Leaf Fig, Pothos, Peace Lily, etc.) and generic botanical fallbacks.
- **Houseplant Catalog (`list_common_houseplants`)**: Curated reference catalog with pet safety classifications.

### 4. Asynchronous Redacted JSON Logging (`logging.py`)
- **Full Audit Trace**: Captures all `USER_QUERY`, `AGENT_INVOCATION`, `LLM_REQUEST`, `LLM_RESPONSE`, `TOOL_INVOCATION`, `TOOL_RESPONSE`, `EXTERNAL_API_REQUEST`, `EXTERNAL_API_RESPONSE`, and `AGENT_RESPONSE` events.
- **Non-Blocking Asynchronous Persistence**: Background tasks write JSONL records to disk asynchronously via thread pools without blocking the main event loop.
- **Automatic Redaction**: Redacts all Google API keys (`AIza...`), bearer tokens, and sensitive dictionary keys (`api_key`, `key`, `token`, `secret`) in stored payloads.
- **Standard Library Proxy**: Exposes all Python standard library `logging` symbols so third-party packages function without circular import or shadowing errors.

### 4. Interactive 2-Page Web Interface
- **Page 1: Chat with Agent**:
  - **Dynamic Model Selection**: Dropdown menu allowing selection between **Gemma 4 26B**, **Gemma 4 31B**, **Gemini 3.5 flash lite**, **Gemini 3.8 flash**, and a **custom text input** to enter any model name manually.
  - Live conversation history feed with per-response model provenance badges.
  - Interactive input field and send button (Enter key enabled).
  - Quick prompt suggestion chips for one-click testing of weather, registry lookups, and compound multi-skill workflows.
- **Page 2: Log Review**:
  - **Table 1 (Conversations)**: Displays `Conversation ID`, `Timestamp`, `User Query`, and `Agent Response`.
  - **Clickable Row Drill-Down**: Clicking any row in Table 1 updates Table 2 below with the sequential events that occurred during that specific conversation.
  - **Table 2 (Events)**: Displays `Timestamp`, `Event Type` (with color-coded badges), `Invoker`, `Target`, and `Short Description`.
  - **Detailed JSON Modal**: Clicking any event row opens a pop-up window showing the complete, human-readable, formatted JSON log with a one-click **Copy JSON** button.

---

## 🛠️ Setup & Execution

### Prerequisites
- Python 3.10+
- Virtual environment with dependencies installed:
```bash
pip install -r requirements.txt
```

### Environment Configuration (`.env`)
Create or edit `.env` with your Google AI Studio API key and desired models:
```env
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your_google_api_key_here

MODEL=gemma-4-26b-a4b-it
FALLBACK_MODEL=gemini-3.5-flash-lite
```

### Running the Web Application
Start the FastAPI server:
```bash
python app.py
```
Or with specific host/port:
```bash
uvicorn app:app --host 0.0.0.0 --port 8080
```
Open your browser and navigate to:
```
http://localhost:8080
```

### Running the Agent in Python / CLI
You can also invoke the agent directly from Python scripts:
```python
import asyncio
from agent import get_agent

async def main():
    agent = get_agent()
    # Compound multi-skill query
    result = await agent.run("What is the current weather and local time in the city where Smith lives?")
    print("Response:", result["response"])

asyncio.run(main())
```

---

## 🧪 Testing

Run the automated test suite with `pytest`:
```bash
pytest -v tests/
```

All 18 unit and integration tests validate:
1. `test_datetime_weather_skill.py`: Nominatim geocoding, Open-Meteo weather fetch, and timezone resolution.
2. `test_house_registry_skill.py`: Case-insensitive containment matching and anti-hallucination non-matches.
3. `test_logging.py`: Asynchronous write operations, payload redaction, and log review query functions.
4. `test_agent.py`: Google GenAI native tool binding, dispatch execution, and response synthesis.
5. `test_integration.py`: Web API endpoints (`/`, `/api/chat`, `/api/conversations`, `/api/events/{id}`) and log audit integrity.
