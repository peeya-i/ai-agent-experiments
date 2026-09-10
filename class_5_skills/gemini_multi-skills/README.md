# Multi-Skill AI Agent

A modular, multi-skill AI agent application built with Google ADK (`google.adk.agents.Agent`) and Google Gemini / Gemma models. The agent accepts natural language terminal input, dynamically selects skills, coordinates multi-step reasoning across skills, answers questions, provides recommendations, and logs all message flows to a security-masked log file.

---

## Features & What the Code Does

### 1. Multi-Skill Architecture
The application features two modular skills adhering to the Gemini skill structure:

- **Skill 1: City Weather and Local Time (`skill_1/`)**
  - **`skill_1/skill_1.md`**: Defines the `city_weather_and_local_time` skill, procedures, parameters, output schemas, and error-handling rules.
  - **`skill_1/tools.py`**: Implements `get_weather(city)` (using OpenWeatherMap with `wttr.in` fallback) and `get_local_time(city)` (using `zoneinfo` with WorldTimeAPI fallback).
- **Skill 2: User House Information (`skill_2/`)**
  - **`skill_2/skill_2.md`**: Directs the LLM to use the tools in the same folder to answer private questions about the user's house.
  - **`skill_2/tools.py`**: Implements `get_house_color()`, `get_house_city()`, and `get_private_house_information(question)`.
    - House color is always **blue**.
    - House city is always **San Jose**.

### 2. Multi-Step Reasoning & LLM Skill Selection
- **Agent Method**: Built with `Agent` from `google.adk.agents`, with all tool callables passed via the `tools` parameter.
- **Skill Selection by LLM**: The LLM can dynamically inspect and activate skills using the `select_skill` tool.
- **Multi-Step Execution**: The agent automatically resolves multi-part queries requiring coordination across multiple skills. For example:
  > *"What is the weather and current time in the city where my house is located?"*
  1. Activates **Skill 2** to discover the house city (`San Jose`).
  2. Activates **Skill 1** to fetch current weather and local time for `San Jose`.
  3. Combines the findings and provides a unified response to the user.

### 3. General Tasks & Recommendations
- Handles general knowledge inquiries and generates thoughtful, tailored recommendations (e.g. books, podcasts, movies, programming tools) without requiring tool calls.

### 4. Human-Readable Security-Masked Logging (`logging.py`)
- Implemented in `logging.py` and called from the main program (`skill_agent_call.py`).
- Marks each prompt with `"=== PROMPT ==="` before processing.
- Logs the actual request and response payloads passed between agent, LLM, tools, and skills:
  - `AGENT -> LLM (GENERATE_CONTENT_REQUEST)`: Full request payload (model, conversation contents, tool declarations).
  - `LLM -> AGENT (GENERATE_CONTENT_RESPONSE)`: Full response payload (parts, function calls, finish reasons, token usage).
  - `AGENT -> TOOL (TOOL_REQUEST)`: Tool invocation with input argument payload.
  - `TOOL -> AGENT (TOOL_RESPONSE)`: Complete tool output and observation payload.
  - `AGENT -> USER (FINAL_RESPONSE)`: Final formatted response.
- Uses `ApiKeyMaskingFilter` to redact all API keys (`[REDACTED_API_KEY]`) for security.
- Human-readable formatted JSON output with ISO timestamps.

---

## Directory Structure

```
gemini_multi-skills/
├── multi-skill_agent.yaml   # Specification requirements
├── README.md                # Documentation and usage guide
├── logging.py               # Custom logging module with API key masking & stdlib proxy
├── skill_agent_call.py      # Main terminal AI agent script calling logging.py
├── multi-skill_agent.log    # Interaction log file
├── .env                     # Environment variables (API keys and model configs)
├── .env.example             # Example environment configuration
├── skill_1/                 # Skill 1 folder
│   ├── skill_1.md           # Skill 1 documentation & schemas
│   ├── tools.py             # Tools: get_weather, get_local_time
│   └── __init__.py
└── skill_2/                 # Skill 2 folder
    ├── skill_2.md           # Skill 2 documentation & schemas
    ├── tools.py             # Tools: get_house_color, get_house_city, get_private_house_information
    └── __init__.py
```

---

## Prerequisites & Setup

### 1. Environment Configuration
Create or verify the `.env` file in the project root:

```ini
# Google AI Studio API key
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your_google_api_key_here

# Model configuration
MODEL="gemma-4-26b-a4b-it"
FALLBACK_MODEL="gemini-3.5-flash-lite"

# Optional: OpenWeatherMap API key (falls back to wttr.in if empty)
OPENWEATHER_API_KEY=your_openweather_key_here
```

### 2. Python Environment
Activate the project's virtual environment:
```bash
source .venv/bin/activate
```

---

## How to Run the Code

Start the terminal agent interactively:

```bash
python skill_agent_call.py
```
*(Or directly using the virtual environment interpreter: `./.venv/bin/python3 skill_agent_call.py`)*

### Example Interactions

#### Single-Skill Query (House Info):
```
You: Where is my house located and what is its color?
Agent: Your house is blue and is located in San Jose.
```

#### Single-Skill Query (Weather & Local Time):
```
You: What is the weather and local time in Paris?
Agent: In Paris, the current weather is partly cloudy with a temperature of 15°C. The local time is 3:11 AM on September 9, 2026 (Europe/Paris, UTC +0200).
```

#### Multi-Step Query (Skill 2 -> Skill 1 Coordination):
```
You: Can you tell me the weather and current time in the city where my house is located?
Agent: In San Jose, where your house is located, the weather is currently overcast with a temperature of 33°C. The current local time is 6:13 PM on September 8, 2026.
```

#### General Task / Recommendation:
```
You: Can you recommend a good book for learning Python?
Agent: Here are some of the best books for learning Python:
1. "Python Crash Course" by Eric Matthes (Best overall beginner guide)
2. "Automate the Boring Stuff with Practical Programming" by Al Sweigart (Best for practical hands-on tasks)
3. "Fluent Python" by Luciano Ramalho (Best for advanced/idiomatic Python)
```

#### Exiting:
```
You: quit
Goodbye!
```

---

## Checking Logs

View the interaction history and message audits:

```bash
cat multi-skill_agent.log
```

Or follow live logs while the agent is running:
```bash
tail -f multi-skill_agent.log
```
