#!/usr/bin/env python3
"""Skill AI Agent

Implements an interactive terminal AI Agent powered by Google Gemini models.
Features:
- Natural language query understanding from terminal input.
- Answers questions and provides helpful recommendations.
- Implements and executes the step-by-step procedure defined in `skill.md` for
  city weather and local time lookup.
- Tool for 2 private questions about the user's house (color: blue, city: San Jose).
- Detailed human-readable logging to `skill_AI_agent.log` capturing every request
  and response payload between Agent, LLM, Tools, and Skills, with strict API key masking
  and '=== PROMPT ===' line markers.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import zoneinfo
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from google import genai
from google.genai import types

# -----------------------------------------------------------------------------
# Configuration & Paths
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()
MODEL_NAME = os.getenv("MODEL", "gemini-3.6-flash").strip()
FALLBACK_MODEL_NAME = os.getenv("FALLBACK_MODEL", "gemini-3.5-flash-lite").strip()

SKILL_FILE = BASE_DIR / "skill.md"
LOG_FILE = BASE_DIR / "skill_AI_agent.log"

if not API_KEY:
    print("[!] Error: GOOGLE_API_KEY is not set. Please configure it in .env or environment.")
    sys.exit(1)


# -----------------------------------------------------------------------------
# Secure Logging System (Human-Readable & API Key Masked)
# -----------------------------------------------------------------------------
def mask_sensitive_data(text: str) -> str:
    """Mask known API keys and common API key patterns."""
    if not text:
        return text

    # Mask configured API keys
    for key in (API_KEY, OPENWEATHER_API_KEY):
        if key and len(key) >= 6:
            text = text.replace(key, "[REDACTED_API_KEY]")

    # Mask Google API keys (AIza... or AQ....)
    text = re.sub(r"AIza[0-9A-Za-z\-_]{35}", "[REDACTED_API_KEY]", text)
    text = re.sub(r"AQ\.[0-9A-Za-z\-_]{30,}", "[REDACTED_API_KEY]", text)

    # Mask query parameters like key=... or appid=...
    text = re.sub(
        r"([?&](?:key|appid|apiKey)=)[^&\s'\"`]+",
        r"\1[REDACTED_API_KEY]",
        text,
    )

    return text


def to_serializable(val: Any) -> Any:
    """Recursively convert SDK structures or custom objects into JSON-friendly dicts."""
    if val is None or isinstance(val, (str, int, float, bool)):
        return val
    if hasattr(val, "value") and isinstance(val.value, (str, int, float, bool)):
        return val.value
    if hasattr(val, "model_dump"):
        try:
            return to_serializable(val.model_dump(exclude_none=True))
        except Exception:
            pass
    if hasattr(val, "to_json_dict"):
        try:
            return to_serializable(val.to_json_dict())
        except Exception:
            pass
    if isinstance(val, dict):
        return {str(k): to_serializable(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        return [to_serializable(item) for item in val]
    return str(val)


def write_raw_log(entry: str) -> None:
    """Safely append a sanitized string entry to skill_AI_agent.log."""
    sanitized = mask_sensitive_data(entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(sanitized)
        if not sanitized.endswith("\n"):
            f.write("\n")


def log_prompt_header(user_query: str) -> None:
    """Log the required '=== PROMPT ===' header and initial user input."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    header = (
        "\n"
        "=== PROMPT ===\n"
        f"{'-' * 80}\n"
        f"[{now}] USER -> AGENT (PROMPT)\n"
        f"{json.dumps({'query': user_query}, indent=2, ensure_ascii=False)}\n"
        f"{'-' * 80}\n"
    )
    write_raw_log(header)


def log_interaction(
    sender: str,
    recipient: str,
    message_type: str,
    payload: Any,
) -> None:
    """Log a human-readable message interaction between Agent, LLM, Tools, Skills, or User."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    clean_payload = to_serializable(payload)
    formatted_body = json.dumps(clean_payload, indent=2, ensure_ascii=False, default=str)

    entry = (
        f"[{now}] {sender.upper()} -> {recipient.upper()} ({message_type.upper()})\n"
        f"{formatted_body}\n"
        f"{'-' * 80}\n"
    )
    write_raw_log(entry)


# -----------------------------------------------------------------------------
# Skill Management (skill.md)
# -----------------------------------------------------------------------------
@dataclass
class SkillDefinition:
    name: str
    description: str
    procedure: str
    raw_content: str


def load_skill_from_file(file_path: Path = SKILL_FILE) -> SkillDefinition:
    """Read and parse skill.md following Google Gemini skill structure."""
    if not file_path.exists():
        return SkillDefinition(
            name="city-weather-and-local-time",
            description="Skill for city weather and local time lookup.",
            procedure="Use get_weather and get_local_time tools for city inquiries.",
            raw_content="No skill.md found.",
        )

    raw_text = file_path.read_text(encoding="utf-8")
    name = "city-weather-and-local-time"
    description = "Skill for retrieving weather metrics and local time for cities."
    procedure = raw_text

    # Parse YAML frontmatter if present
    if raw_text.startswith("---"):
        parts = raw_text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                name = fm.get("name", name)
                description = fm.get("description", description)
                procedure = parts[2].strip()
            except Exception:
                pass

    return SkillDefinition(
        name=name,
        description=description,
        procedure=procedure,
        raw_content=raw_text,
    )


# -----------------------------------------------------------------------------
# Skills & Tools Implementations
# -----------------------------------------------------------------------------
CITY_TIMEZONES: dict[str, str] = {
    # North America
    "san jose": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "los angeles": "America/Los_Angeles",
    "seattle": "America/Los_Angeles",
    "portland": "America/Los_Angeles",
    "las vegas": "America/Los_Angeles",
    "phoenix": "America/Phoenix",
    "denver": "America/Denver",
    "salt lake city": "America/Denver",
    "chicago": "America/Chicago",
    "austin": "America/Chicago",
    "dallas": "America/Chicago",
    "houston": "America/Chicago",
    "new york": "America/New_York",
    "boston": "America/New_York",
    "washington": "America/New_York",
    "washington dc": "America/New_York",
    "miami": "America/New_York",
    "atlanta": "America/New_York",
    "toronto": "America/Toronto",
    "montreal": "America/Toronto",
    "vancouver": "America/Vancouver",
    "mexico city": "America/Mexico_City",
    # Europe
    "london": "Europe/London",
    "dublin": "Europe/Dublin",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "munich": "Europe/Berlin",
    "frankfurt": "Europe/Berlin",
    "madrid": "Europe/Madrid",
    "barcelona": "Europe/Madrid",
    "rome": "Europe/Rome",
    "milan": "Europe/Rome",
    "amsterdam": "Europe/Amsterdam",
    "brussels": "Europe/Brussels",
    "vienna": "Europe/Vienna",
    "zurich": "Europe/Zurich",
    "geneva": "Europe/Zurich",
    "stockholm": "Europe/Stockholm",
    "oslo": "Europe/Oslo",
    "copenhagen": "Europe/Copenhagen",
    "helsinki": "Europe/Helsinki",
    "athens": "Europe/Athens",
    "istanbul": "Europe/Istanbul",
    "warsaw": "Europe/Warsaw",
    "prague": "Europe/Prague",
    # Asia & Middle East
    "tokyo": "Asia/Tokyo",
    "kyoto": "Asia/Tokyo",
    "osaka": "Asia/Tokyo",
    "seoul": "Asia/Seoul",
    "beijing": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai",
    "shenzhen": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong",
    "taipei": "Asia/Taipei",
    "singapore": "Asia/Singapore",
    "bangkok": "Asia/Bangkok",
    "kuala lumpur": "Asia/Kuala_Lumpur",
    "jakarta": "Asia/Jakarta",
    "manila": "Asia/Manila",
    "mumbai": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "new delhi": "Asia/Kolkata",
    "bangalore": "Asia/Kolkata",
    "bengaluru": "Asia/Kolkata",
    "dubai": "Asia/Dubai",
    "abu dhabi": "Asia/Dubai",
    "doha": "Asia/Qatar",
    "riyadh": "Asia/Riyadh",
    "tel aviv": "Asia/Jerusalem",
    # Australia & Oceania
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "brisbane": "Australia/Brisbane",
    "perth": "Australia/Perth",
    "auckland": "Pacific/Auckland",
    # South America & Africa
    "sao paulo": "America/Sao_Paulo",
    "rio de janeiro": "America/Sao_Paulo",
    "buenos aires": "America/Argentina/Buenos_Aires",
    "santiago": "America/Santiago",
    "cairo": "Africa/Cairo",
    "johannesburg": "Africa/Johannesburg",
    "nairobi": "Africa/Nairobi",
}


def get_weather(city: str) -> dict[str, Any]:
    """Retrieve current weather metrics for a specified city (via skill.md)."""
    clean_city = city.strip()
    encoded_city = urllib.parse.quote(clean_city)

    # 1. Use OpenWeatherMap if an API key is available
    if OPENWEATHER_API_KEY:
        owm_url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={encoded_city}&appid={OPENWEATHER_API_KEY}&units=metric"
        )
        try:
            req = urllib.request.Request(owm_url, headers={"User-Agent": "skill_AI_agent/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return {
                "city": data.get("name", clean_city),
                "temperature_c": data.get("main", {}).get("temp"),
                "feels_like_c": data.get("main", {}).get("feels_like"),
                "condition": (data.get("weather") or [{}])[0].get("description", "Clear").title(),
                "humidity_percent": data.get("main", {}).get("humidity"),
                "wind_speed": f"{data.get('wind', {}).get('speed', 'N/A')} m/s",
            }
        except Exception:
            pass

    # 2. Free, reliable fallback via wttr.in JSON format
    wttr_url = f"https://wttr.in/{encoded_city}?format=j1"
    try:
        req = urllib.request.Request(wttr_url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        curr = data["current_condition"][0]
        desc = curr.get("weatherDesc", [{}])[0].get("value", "Clear").strip()
        return {
            "city": clean_city.title(),
            "temperature_c": curr.get("temp_C"),
            "feels_like_c": curr.get("FeelsLikeC"),
            "condition": desc,
            "humidity_percent": curr.get("humidity"),
            "wind_speed": f"{curr.get('windspeedKmph')} km/h",
        }
    except Exception as err:
        return {
            "city": clean_city.title(),
            "error": f"Unable to fetch weather data for '{clean_city}': {err}",
        }


def get_local_time(city: str) -> dict[str, Any]:
    """Retrieve current local time, date, and timezone for a specified city (via skill.md)."""
    clean_city = city.strip().lower()

    # Match in local timezone dictionary
    tz_name = CITY_TIMEZONES.get(clean_city)
    if not tz_name:
        for known_city, known_tz in CITY_TIMEZONES.items():
            if known_city in clean_city or clean_city in known_city:
                tz_name = known_tz
                break

    if tz_name:
        try:
            tz = zoneinfo.ZoneInfo(tz_name)
            now = datetime.datetime.now(tz)
            return {
                "city": city.strip().title(),
                "local_time": now.strftime("%I:%M:%S %p"),
                "local_date": now.strftime("%Y-%m-%d"),
                "timezone": tz_name,
                "utc_offset": now.strftime("%z"),
            }
        except Exception as err:
            pass

    # Fallback to WorldTimeAPI
    wta_url = f"https://worldtimeapi.org/api/timezone/{urllib.parse.quote(clean_city)}"
    try:
        req = urllib.request.Request(wta_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return {
            "city": city.strip().title(),
            "local_time": data.get("datetime", "")[11:19],
            "local_date": data.get("datetime", "")[:10],
            "timezone": data.get("timezone"),
            "utc_offset": data.get("utc_offset"),
        }
    except Exception:
        # Ultimate fallback using UTC with notice
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        return {
            "city": city.strip().title(),
            "local_time": utc_now.strftime("%I:%M:%S %p (UTC)"),
            "local_date": utc_now.strftime("%Y-%m-%d"),
            "timezone": "UTC (default fallback)",
            "utc_offset": "+0000",
            "note": f"Exact timezone for '{city}' not recognized; returned standard UTC.",
        }


# -----------------------------------------------------------------------------
# Private House Information Tool
# -----------------------------------------------------------------------------
USER_HOUSE_DATA = {
    "house_color": "blue",
    "house_city": "San Jose",
}


def get_private_house_information(question: str = "", query_type: str = "all") -> dict[str, Any]:
    """Retrieve private details about the user's house (color: blue, city: San Jose).

    Args:
        question: The user's question regarding their house.
        query_type: Specific attribute requested ('color', 'city', 'location', or 'all').
    """
    text = (f"{question} {query_type}").lower()
    has_color = any(k in text for k in ("color", "colour", "paint"))
    has_city = any(k in text for k in ("city", "location", "located", "where", "town"))

    if has_color and not has_city:
        return {
            "house_color": USER_HOUSE_DATA["house_color"],
            "answer": f"The color of the user's house is {USER_HOUSE_DATA['house_color']}.",
        }
    if has_city and not has_color:
        return {
            "house_city": USER_HOUSE_DATA["house_city"],
            "answer": f"The user's house is located in {USER_HOUSE_DATA['house_city']}.",
        }

    return {
        "house_color": USER_HOUSE_DATA["house_color"],
        "house_city": USER_HOUSE_DATA["house_city"],
        "answer": (
            f"The user's house is {USER_HOUSE_DATA['house_color']} and is located in "
            f"{USER_HOUSE_DATA['house_city']}."
        ),
    }


# -----------------------------------------------------------------------------
# Gemini Tool Declarations & Dispatcher
# -----------------------------------------------------------------------------
AGENT_TOOLS_DECLARATION = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_weather",
            description=(
                "Retrieve current weather conditions (temperature, condition, humidity, wind) "
                "for a specified city following the active skill.md procedure."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "city": types.Schema(
                        type=types.Type.STRING,
                        description="The city name to look up weather for (e.g., 'San Jose', 'Paris').",
                    )
                },
                required=["city"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_local_time",
            description=(
                "Retrieve the current local time, date, and timezone for a specified city "
                "following the active skill.md procedure."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "city": types.Schema(
                        type=types.Type.STRING,
                        description="The city name to look up current local time for.",
                    )
                },
                required=["city"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_private_house_information",
            description=(
                "Answer private questions about the user's house: the color of the house "
                "(which is blue) and the city where the house is located (which is San Jose)."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "question": types.Schema(
                        type=types.Type.STRING,
                        description="The question or attribute regarding the user's house.",
                    ),
                    "query_type": types.Schema(
                        type=types.Type.STRING,
                        description="Specific attribute requested: 'color', 'city', or 'all'.",
                    ),
                },
            ),
        ),
    ]
)

TOOL_DISPATCHER = {
    "get_weather": get_weather,
    "get_local_time": get_local_time,
    "get_private_house_information": get_private_house_information,
}


def describe_tools(tool_decl: types.Tool) -> list[dict[str, Any]]:
    """Format tool declarations for human-readable logging."""
    return [
        {
            "name": decl.name,
            "description": decl.description,
            "parameters": to_serializable(decl.parameters),
        }
        for decl in (tool_decl.function_declarations or [])
    ]


def extract_plain_text(response: Any) -> str | None:
    """Safely extract plain text from Gemini candidate response parts."""
    try:
        if not response.candidates:
            return None
        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            return None
        texts = [
            p.text
            for p in candidate.content.parts
            if getattr(p, "text", None) and not getattr(p, "thought", False)
        ]
        if not texts:
            texts = [p.text for p in candidate.content.parts if getattr(p, "text", None)]
        return "".join(texts).strip() if texts else None
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Agent Turn Execution (Step-by-Step Skill & LLM Orchestration)
# -----------------------------------------------------------------------------
def run_agent_turn(
    client: genai.Client,
    user_query: str,
    active_model: str,
    skill: SkillDefinition,
) -> str:
    """Execute one complete user turn: consult skill, invoke Gemini, dispatch tools, log all steps."""

    # 1. Log Skill invocation / consultation
    log_interaction(
        sender="agent",
        recipient="skill",
        message_type="consult_skill",
        payload={
            "skill_file": str(SKILL_FILE.name),
            "skill_name": skill.name,
            "user_query": user_query,
        },
    )

    log_interaction(
        sender="skill",
        recipient="agent",
        message_type="skill_procedure_loaded",
        payload={
            "skill_name": skill.name,
            "description": skill.description,
            "procedure": skill.procedure,
        },
    )

    # 2. Build system instructions combining general capability, skill procedure, and private tool
    system_instruction = (
        "You are an intelligent, helpful AI Agent. You understand natural language, answer questions, "
        "and provide insightful recommendations.\n\n"
        "### Step-by-Step Skill Procedure (from skill.md):\n"
        f"{skill.procedure}\n\n"
        "### House Information Tool Rules:\n"
        "- When the user asks about their house, use the `get_private_house_information` tool.\n"
        "- The house color is blue.\n"
        "- The house is located in San Jose.\n\n"
        "Always be concise, accurate, friendly, and helpful."
    )

    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part.from_text(text=user_query)])
    ]

    config = types.GenerateContentConfig(
        tools=[AGENT_TOOLS_DECLARATION],
        system_instruction=system_instruction,
        temperature=0.7,
    )

    max_tool_iterations = 6
    for iteration in range(max_tool_iterations):
        # Log Agent -> LLM Request
        log_interaction(
            sender="agent",
            recipient="llm",
            message_type="generate_content_request",
            payload={
                "iteration": iteration + 1,
                "model": active_model,
                "system_instruction": system_instruction,
                "tools": describe_tools(AGENT_TOOLS_DECLARATION),
                "contents": to_serializable(contents),
            },
        )

        response = client.models.generate_content(
            model=active_model,
            contents=contents,
            config=config,
        )

        function_calls = response.function_calls or []
        resp_text = extract_plain_text(response)

        # Log LLM -> Agent Response
        log_interaction(
            sender="llm",
            recipient="agent",
            message_type="generate_content_response",
            payload={
                "iteration": iteration + 1,
                "model": active_model,
                "text": resp_text,
                "function_calls": [
                    {"name": fc.name, "args": fc.args} for fc in function_calls
                ],
            },
        )

        # If LLM didn't call any tools, we have the final answer
        if not function_calls:
            return resp_text or "I am here to assist you! How can I help?"

        # Append candidate response to conversation history
        if response.candidates and response.candidates[0].content:
            contents.append(response.candidates[0].content)

        # Dispatch tool calls
        tool_response_parts: list[types.Part] = []
        for fc in function_calls:
            tool_name = fc.name
            tool_args = fc.args or {}

            # Identify if this is a skill tool or house info tool
            recipient_entity = f"tool:{tool_name}"
            if tool_name in ("get_weather", "get_local_time"):
                sender_entity = "skill"
            else:
                sender_entity = "agent"

            # Log Tool Call Request
            log_interaction(
                sender=sender_entity,
                recipient=recipient_entity,
                message_type="tool_call_request",
                payload={"arguments": tool_args},
            )

            # Execute tool
            if tool_name in TOOL_DISPATCHER:
                try:
                    tool_result = TOOL_DISPATCHER[tool_name](**tool_args)
                except Exception as exc:
                    tool_result = {"error": f"Tool execution error: {exc}"}
            else:
                tool_result = {"error": f"Unrecognized tool: {tool_name}"}

            # Log Tool Response
            log_interaction(
                sender=recipient_entity,
                recipient=sender_entity,
                message_type="tool_call_response",
                payload={"result": tool_result},
            )

            tool_response_parts.append(
                types.Part.from_function_response(
                    name=tool_name,
                    response=tool_result,
                )
            )

        contents.append(types.Content(role="user", parts=tool_response_parts))

    return "Completed maximum tool iterations. Please ask if you need further clarification."


def ask_agent(client: genai.Client, user_query: str) -> str:
    """Send user query to Gemini with automatic model fallback."""
    skill = load_skill_from_file(SKILL_FILE)
    models_to_try = [MODEL_NAME]
    if FALLBACK_MODEL_NAME and FALLBACK_MODEL_NAME != MODEL_NAME:
        models_to_try.append(FALLBACK_MODEL_NAME)

    last_error: Exception | None = None
    for model in models_to_try:
        try:
            return run_agent_turn(client, user_query, model, skill)
        except Exception as err:
            last_error = err
            log_interaction(
                sender="agent",
                recipient="system",
                message_type="model_fallback_triggered",
                payload={"failed_model": model, "error": str(err)},
            )
            print(f"[!] Notice: Model '{model}' error ({err}). Trying fallback...")

    return f"Unable to complete request across configured models: {last_error}"


# -----------------------------------------------------------------------------
# Terminal Interaction Loop
# -----------------------------------------------------------------------------
def main() -> None:
    client = genai.Client(api_key=API_KEY)
    skill = load_skill_from_file(SKILL_FILE)

    print("=" * 65)
    print("      Skill AI Agent — Powered by Google Gemini       ")
    print("=" * 65)
    print(f"• Active Skill: {skill.name} (from skill.md)")
    print(f"• Primary Model: {MODEL_NAME} (Fallback: {FALLBACK_MODEL_NAME})")
    print("• Log File: skill_AI_agent.log")
    print("-" * 65)
    print("Capabilities:")
    print(" 1. Ask about city weather (e.g., 'What is the weather in Tokyo?')")
    print(" 2. Ask about city local time (e.g., 'What time is it in Paris?')")
    print(" 3. Ask about both (e.g., 'Give me the weather and time in London')")
    print(" 4. Ask about your house (color / city location)")
    print(" 5. Ask general questions or request recommendations")
    print("Type 'exit' or 'quit' to terminate the session.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended. Goodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        # Log prompt marker and user input
        log_prompt_header(user_input)

        # Execute agent workflow
        response_text = ask_agent(client, user_input)

        # Log agent final answer to user
        log_interaction(
            sender="agent",
            recipient="user",
            message_type="final_response",
            payload={"response": response_text},
        )

        print(f"\nAgent: {response_text}\n")


if __name__ == "__main__":
    main()
