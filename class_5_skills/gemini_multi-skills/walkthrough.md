# Multi-Skill AI Agent Implementation Walkthrough

The multi-skill AI agent system has been implemented based on the requirements in [`multi-skill_agent.yaml`](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/multi-skill_agent.yaml).

## Architecture & Components

```
gemini_multi-skills/
├── multi-skill_agent.yaml   # Specification requirements
├── README.md                # Usage guide and documentation
├── skill_1/
│   ├── skill_1.md          # Gemini skill definition for City Weather & Local Time
│   ├── tools.py            # Python tools (get_weather, get_local_time)
│   └── __init__.py
├── skill_2/
│   ├── skill_2.md          # Gemini skill definition for User House Information
│   ├── tools.py            # Python tools (get_house_color, get_house_city, get_private_house_information)
│   └── __init__.py
├── logging.py              # Custom logging module with API key masking & stdlib proxy
├── skill_agent_call.py     # Main terminal AI agent using google.adk.agents.Agent
└── multi-skill_agent.log   # Structured, human-readable message audit log
```

---

## Changes Implemented

### 1. Skill 1: City Weather & Local Time
- **Files**: [`skill_1/skill_1.md`](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/skill_1/skill_1.md), [`skill_1/tools.py`](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/skill_1/tools.py), [`skill_1.md`](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/skill_1.md).
- **Structure**: Follows standard Gemini markdown skill format with YAML frontmatter, name, description, procedure, tool schemas, and error handling.
- **Tools**:
  - `get_weather(city: str)`: Queries OpenWeatherMap (when configured) with fallback to `wttr.in`.
  - `get_local_time(city: str)`: Computes local time, date, and timezone using `zoneinfo` with WorldTimeAPI fallback.

### 2. Skill 2: User House Information
- **Files**: [`skill_2/skill_2.md`](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/skill_2/skill_2.md), [`skill_2/tools.py`](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/skill_2/tools.py), [`skill_2.md`](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/skill_2.md).
- **Structure**: Tells the LLM to use the tools in the same folder to answer questions about the user's house.
- **Tools**:
  - `get_house_color()`: Returns color `blue`.
  - `get_house_city()`: Returns city `San Jose`.
  - `get_private_house_information(question: str)`: Flexible query tool handling house color, location, or both.

### 3. Logging Module
- **File**: [`logging.py`](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/logging.py).
- Safely exposes all Python standard library `logging` symbols so third-party packages (`google.adk`, `google.genai`) function normally without circular import or shadowing errors.
- Sets up [`multi-skill_agent.log`](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/multi-skill_agent.log) with human-readable headers and formatted JSON payloads.
- `ApiKeyMaskingFilter`: Redacts API keys (`[REDACTED_API_KEY]`).
- `log_prompt(query)`: Prepends each user prompt with `"=== PROMPT ==="`.
- `log_event(sender, recipient, message_type, payload)`: Logs message exchanges across all boundaries.

### 4. Main Multi-Skill AI Agent
- **File**: [`skill_agent_call.py`](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/skill_agent_call.py).
- Uses `Agent` from `google.adk.agents` and passes tools in the `tools` parameter:
  ```python
  agent = Agent(
      name="multi_skill_agent",
      model=Gemini(model=self.active_model),
      tools=self.tools,  # Passed in tools parameter
      instruction=self.instruction,
  )
  ```
- **Skill Selection by LLM**: Exposes `select_skill(skill_name: str)` for on-demand skill activation.
- **Multi-Step Coordination**: Handles complex queries spanning multiple skills (e.g. querying house city from `skill_2`, then fetching weather and time for that city from `skill_1`).
- **Recommendations & General Questions**: Directly provides rich recommendations (books, tech, etc.).
- **Automatic Fallback**: Gracefully falls back from primary model (`gemma-4-26b-a4b-it`) to `gemini-3.5-flash-lite` if quotas or errors are encountered.

---

## Verification & Testing

### 1. Individual Tool Tests
Ran automated validation on all tool functions:
- `get_weather("San Jose")` -> Overcast, 33°C.
- `get_local_time("San Jose")` -> Formatted 12-hour local time, America/Los_Angeles timezone.
- `get_house_color()` -> `{"color": "blue"}`.
- `get_house_city()` -> `{"city": "San Jose"}`.

### 2. Multi-Step Query Verification
Tested with the query:
> *"Can you tell me the weather and current time in the city where my house is located?"*

**Result**:
```
Agent: In San Jose, where your house is located, the weather is currently overcast with a temperature of 33°C (feeling like 30°C). The humidity is at 23% and the wind speed is 11 km/h. The current local time is 6:13 PM on September 8, 2026.
```

### 3. Log Audit ([`multi-skill_agent.log`](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/multi-skill_agent.log))
- Verified `"=== PROMPT ==="` is inserted before every prompt.
- Verified message sequence:
  1. `USER -> AGENT (PROMPT)`
  2. `AGENT -> LLM (ADK_AGENT_REQUEST)`
  3. `AGENT -> SKILL_2:HOUSE_CITY (TOOL_CALL)`
  4. `SKILL_2:HOUSE_CITY -> AGENT (TOOL_RESPONSE)`
  5. `AGENT -> SKILL_1:WEATHER (TOOL_CALL)`
  6. `SKILL_1:WEATHER -> EXTERNAL_SERVICE (WTTR_REQUEST)`
  7. `EXTERNAL_SERVICE -> SKILL_1:WEATHER (WTTR_RESPONSE)`
  8. `SKILL_1:WEATHER -> AGENT (TOOL_RESPONSE)`
  9. `AGENT -> SKILL_1:LOCAL_TIME (TOOL_CALL)`
  10. `SKILL_1:LOCAL_TIME -> AGENT (TOOL_RESPONSE)`
  11. `LLM -> AGENT (ADK_AGENT_RESPONSE)`
  12. `AGENT -> USER (FINAL_RESPONSE)`
- Verified API key redaction: No raw API keys appear in the log file.

---

## Running the Agent

To start the agent interactively from the terminal:
```bash
./.venv/bin/python3 skill_agent_call.py
```
Type your query at the `You: ` prompt, or type `quit` or `exit` to stop.
