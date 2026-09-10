# AI Agent Experiments: Class Skills

A collection of lightweight Python AI agent patterns powered by the Google GenAI SDK (`google-genai`), demonstrating multi-agent validation loops and ReAct tool invocation.

---

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Environment Configuration](#environment-configuration)
- [Scripts Overview](#scripts-overview)
  - [1. Code Generation & Validation Pipeline (`codegen_agent_pipeline.py`)](#1-code-generation--validation-pipeline-codegen_agent_pipelinepy)
  - [2. Weather Skill ReAct Agent (`get_weather_skill.py`)](#2-weather-skill-react-agent-get_weather_skillpy)
- [Dependencies](#dependencies)

---

## Prerequisites
- Python 3.10+
- A Google Gemini API key (from [Google AI Studio](https://aistudio.google.com/))

---

## Installation & Setup

1. **Clone or navigate to the repository directory:**
   ```bash
   cd simple_skills
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Environment Configuration

Create a `.env` file in the root directory (or copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` with your API key and model preferences:

```ini
# Google AI Studio API key
GOOGLE_API_KEY="your-gemini-api-key-here"

# Optional: Preferred model configuration
MODEL="gemini-3.5-flash"
FALLBACK_MODEL="gemini-3.5-flash-lite"
```

> **Note**: The scripts check for both `GEMINI_API_KEY` and `GOOGLE_API_KEY`. If primary model calls fail, both scripts automatically retry with `FALLBACK_MODEL`.

---

## Scripts Overview

### 1. Code Generation & Validation Pipeline (`codegen_agent_pipeline.py`)

#### What It Does
Implements an **iterative multi-agent feedback loop** between two distinct LLM personas:
- **Coder Agent**: Generates raw, functional Python code according to requirements and past feedback.
- **Validator Agent (QA)**: Audits the generated code for syntax, logic bugs, edge cases, or missing requirements. It returns either:
  - `PASSED`: Code is verified and approved.
  - `FAIL: <details>`: Specific critique and bug reports.
- **Feedback Loop**: If validation fails, the critique is routed back to the Coder Agent for correction (up to 3 iterations).

#### How to Use
- **With a command-line prompt:**
  ```bash
  python codegen_agent_pipeline.py "Write a python function called divide_numbers that gracefully returns 0 on division by zero"
  ```
- **Interactively:**
  ```bash
  python codegen_agent_pipeline.py
  # Enter your coding task prompt (or press Enter for default):
  ```

---

### 2. Weather Skill ReAct Agent (`get_weather_skill.py`)

#### What It Does
Implements an autonomous **ReAct (Reasoning + Acting) pattern** with tool execution:
- **Reasoning Loop**: Follows a cycle of `Thought` ➔ `Action` ➔ `Observation` ➔ `Answer`.
- **Tool Execution**: When the agent decides it needs live data, it emits an action:
  ```json
  Action: {"tool": "get_weather", "arg": "<city>"}
  ```
- **Live Weather Lookup**: Queries the free `wttr.in` endpoint to obtain current conditions without requiring a dedicated third-party weather API key.
- **Observation Feeding**: Passes the tool output back to the model as user context until a final answer is produced.

#### How to Use
- **With a command-line query:**
  ```bash
  python get_weather_skill.py "What is the weather in Tokyo?"
  ```
  ```bash
  python get_weather_skill.py "What is the temperature in San Jose, California?"
  ```
- **Interactively:**
  ```bash
  python get_weather_skill.py
  # Enter your weather query (or press Enter for default):
  ```

---

## Dependencies

Defined in [requirements.txt](requirements.txt):
- `google-genai>=2.19.0`: Official Google GenAI SDK for Gemini models.
- `python-dotenv>=1.0.0`: Loads environment variables from `.env`.
- `requests>=2.31.0`: HTTP library used for weather API requests.
