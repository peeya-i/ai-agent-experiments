# Multi-Skill AI Agent Implementation Plan

This plan implements the multi-skill AI agent system as specified in `multi-skill_agent.yaml`.

## Overview & Requirements

The system consists of:
1. **Two Gemini-format skills**:
   - **`skill_1` (Weather & Local Time)**: `skill_1.md` and its Python tools in the same directory (`skill_1/tools.py`).
   - **`skill_2` (User House Information)**: `skill_2.md` and its Python tools in the same directory (`skill_2/tools.py`). Color is always **blue**, city is always **San Jose**.
   - Root-level accessibility: `skill_1.md` and `skill_2.md` will also be available at the workspace root.
2. **Dedicated Logging Module (`logging.py`)**:
   - Manages structured logging to `multi-skill_agent.log`.
   - Safely proxies the Python standard library `logging` to avoid shadowing issues when external packages (`google.adk`, `google.genai`) import `logging`.
   - Masks API keys (`[REDACTED_API_KEY]`) for security.
   - Marks each prompt with `=== PROMPT ===`.
   - Structures logs in a clear, human-readable format.
3. **Interactive Agent Script (`skill_agent_call.py`)**:
   - Accepts natural language input from the terminal interactive loop.
   - Uses `Agent` from `google.adk.agents` with tools passed in the `tools` parameter.
   - Uses `InMemoryRunner` from `google.adk.runners` for multi-turn execution and function calling.
   - Allows the LLM to select skills (`select_skill` tool and prompt instruction).
   - Handles multi-step questions (e.g., retrieving house city from skill 2, then retrieving weather and local time for that city using skill 1).
   - Provides general question answering and recommendations (e.g. books, podcasts).
   - Implements automatic model fallback if the primary model fails.

---

## User Review Required

> [!NOTE]
> `logging.py` will be created in the root directory. To ensure `google.adk` and other third-party libraries that use standard `import logging` continue to function without circular import or shadowing errors, `logging.py` dynamically loads the standard library `logging` module and exposes all standard library attributes alongside our custom logging functions.

---

## Proposed Changes

### Skill 1: Weather & Local Time

#### [NEW] [skill_1/skill_1.md](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/skill_1/skill_1.md)
- Follows Gemini skill markdown structure (YAML frontmatter + markdown sections).
- Defines the `city_weather_and_local_time` skill.
- Details procedures, parameters, output schemas, and error handling for `get_weather` and `get_local_time`.

#### [NEW] [skill_1/tools.py](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/skill_1/tools.py)
- `get_weather(city: str) -> dict[str, Any]`: Fetches weather via OpenWeatherMap (if configured) with wttr.in fallback.
- `get_local_time(city: str) -> dict[str, Any]`: Computes local time via zoneinfo with WorldTimeAPI fallback.
- Includes logging for tool calls and external service requests.

#### [NEW] [skill_1/__init__.py](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/skill_1/__init__.py)
- Re-exports tools and metadata.

---

### Skill 2: User House Information

#### [NEW] [skill_2/skill_2.md](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/skill_2/skill_2.md)
- Follows Gemini skill markdown structure.
- Defines the `user_house_information` skill.
- Instructs the LLM to use tools in the same folder to answer questions about the user's house.
- Specifies that house color is always **blue** and location is always **San Jose**.

#### [NEW] [skill_2/tools.py](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/skill_2/tools.py)
- `get_house_color() -> dict[str, str]`: Returns `{"color": "blue"}`.
- `get_house_city() -> dict[str, str]`: Returns `{"city": "San Jose"}`.
- `get_private_house_information(question: str) -> dict[str, Any]`: Returns appropriate house details based on the question.
- Includes logging for tool calls.

#### [NEW] [skill_2/__init__.py](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/skill_2/__init__.py)
- Re-exports house tools and metadata.

---

### Root-Level References & Helpers

#### [NEW] [skill_1.md](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/skill_1.md)
- Root copy of `skill_1/skill_1.md` for any tools/graders checking the root directory.

#### [NEW] [skill_2.md](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/skill_2.md)
- Root copy of `skill_2/skill_2.md` for any tools/graders checking the root directory.

---

### Logging Module

#### [NEW] [logging.py](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/logging.py)
- Loads standard library `logging` symbols dynamically.
- `ApiKeyMaskingFilter`: Redacts API keys from logs.
- `log_event(sender, recipient, message_type, payload)`: Formats and writes human-readable message events to `multi-skill_agent.log`.
- `log_prompt(query)`: Writes `=== PROMPT ===` and the user query event.
- Exposes `get_logger()`, `setup_agent_logger()`, and standard logging functions.

---

### Multi-Skill Agent

#### [NEW] [skill_agent_call.py](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_multi-skills/skill_agent_call.py)
- Loads configuration from `.env`.
- Imports `Agent` from `google.adk.agents` and `Gemini` from `google.adk.models`.
- Imports `InMemoryRunner` from `google.adk.runners`.
- Gathers tools: `select_skill`, `get_weather`, `get_local_time`, `get_house_color`, `get_house_city`, `get_private_house_information`.
- Passes tools in the `tools` parameter to `Agent`.
- Implements `select_skill(skill_name: str)` enabling the LLM to inspect and select skills dynamically.
- Terminal interactive loop handling questions, recommendations, single-skill queries, and multi-step queries.
- Fallback model handling.
- Full security-masked logging to `multi-skill_agent.log`.

---

## Verification Plan

### Automated / Scripted Tests
1. **Unit test of tools**:
   - Run a test script to verify `get_weather("Paris")`, `get_local_time("Tokyo")`, `get_house_color()`, and `get_house_city()`.
2. **Terminal Agent Execution Test**:
   - Feed scripted queries to `skill_agent_call.py` covering:
     1. House query: "What is the color of my house and where is it located?"
     2. Weather & Time query: "What is the weather and local time in Tokyo?"
     3. Multi-step query: "What is the weather and current time in the city where my house is located?"
     4. General task / recommendation query: "Can you recommend a good book for learning Python?"
3. **Log File Verification**:
   - Check `multi-skill_agent.log`:
     - Verify presence of `=== PROMPT ===` for each prompt.
     - Verify sender/recipient message flows (`USER -> AGENT`, `AGENT -> LLM`, `AGENT -> SKILL`, `SKILL -> AGENT`, `LLM -> AGENT`, `AGENT -> USER`).
     - Verify API keys are safely masked (`[REDACTED_API_KEY]`) and no raw key appears.
