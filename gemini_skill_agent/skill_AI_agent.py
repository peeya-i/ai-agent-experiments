#!/usr/bin/env python3
"""Skill AI Agent

Implements a terminal AI agent that accepts natural language input, invokes Google
Gemini / Gemma models, provides answers and recommendations, follows the procedure
in `skill.md` for weather and local time lookup for specific cities, and uses a private
tool to answer questions about the user's house (color: blue, city: San Jose).
All message interactions between the agent, LLM, tools, and skills are logged
to `skill_AI_agent.log` with human-readable formatting and API keys masked.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import sys
import urllib.parse
import urllib.request
import zoneinfo
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

# -----------------------------------------------------------------------------
# Configuration & Environment
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("GOOGLE_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
MODEL_NAME = os.getenv("MODEL", "gemma-4-26b-a4b-it")
FALLBACK_MODEL_NAME = os.getenv("FALLBACK_MODEL", "gemini-3.5-flash-lite")

SKILL_FILE = BASE_DIR / "skill.md"
LOG_FILE = BASE_DIR / "skill_AI_agent.log"
ALT_LOG_FILE = BASE_DIR / "ai_agent.log"

if not API_KEY:
    print("[!] Error: GOOGLE_API_KEY is not set. Please configure it in .env or environment.")
    sys.exit(1)

SKILL_INSTRUCTIONS = (
    SKILL_FILE.read_text(encoding="utf-8")
    if SKILL_FILE.exists()
    else "No skill.md file found."
)


# -----------------------------------------------------------------------------
# Logging System with API Key Masking
# -----------------------------------------------------------------------------
class ApiKeyMaskingFilter(logging.Filter):
    """Masks all known API keys in log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for key in (API_KEY, OPENWEATHER_API_KEY):
            if key and len(key) > 5:
                message = message.replace(key, "[REDACTED_API_KEY]")
        record.msg = message
        record.args = ()
        return True


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("skill_AI_agent")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    masking_filter = ApiKeyMaskingFilter()

    for path in (LOG_FILE, ALT_LOG_FILE):
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(formatter)
        handler.addFilter(masking_filter)
        logger.addHandler(handler)

    return logger


logger = setup_logger()


@dataclass
class LogEvent:
    sender: str
    recipient: str
    message_type: str
    payload: Any
    timestamp: str


def to_serializable(val: Any) -> Any:
    """Convert SDK types or objects into clean JSON-serializable dictionaries."""
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


def log_event(sender: str, recipient: str, message_type: str, payload: Any) -> None:
    """Record a structured, human-readable message exchange in the log."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    event = LogEvent(
        sender=sender,
        recipient=recipient,
        message_type=message_type,
        payload=to_serializable(payload),
        timestamp=now,
    )
    header = f"[{event.timestamp}] {sender.upper()} -> {recipient.upper()} ({message_type.upper()})"
    body = json.dumps(asdict(event), indent=2, ensure_ascii=False, default=str)
    logger.info("%s\n%s", header, body)


def log_prompt(user_query: str) -> None:
    """Record the prompt start line required by specification."""
    logger.info("=== PROMPT ===")
    log_event("user", "agent", "prompt", {"query": user_query})


# -----------------------------------------------------------------------------
# Skills & External Service Implementations
# -----------------------------------------------------------------------------
CITY_TIMEZONES: dict[str, str] = {
    "san jose": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "los angeles": "America/Los_Angeles",
    "seattle": "America/Los_Angeles",
    "new york": "America/New_York",
    "boston": "America/New_York",
    "chicago": "America/Chicago",
    "austin": "America/Chicago",
    "denver": "America/Denver",
    "london": "Europe/London",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "madrid": "Europe/Madrid",
    "rome": "Europe/Rome",
    "amsterdam": "Europe/Amsterdam",
    "tokyo": "Asia/Tokyo",
    "kyoto": "Asia/Tokyo",
    "beijing": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong",
    "singapore": "Asia/Singapore",
    "seoul": "Asia/Seoul",
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "dubai": "Asia/Dubai",
    "mumbai": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "bangalore": "Asia/Kolkata",
    "rio de janeiro": "America/Sao_Paulo",
    "sao paulo": "America/Sao_Paulo",
    "cairo": "Africa/Cairo",
    "toronto": "America/Toronto",
    "vancouver": "America/Vancouver",
}


def get_weather(city: str) -> dict[str, Any]:
    """Retrieve current weather information for a specified city (via skill.md)."""
    clean_city = city.strip()
    encoded_city = urllib.parse.quote(clean_city)

    # 1. Try OpenWeatherMap if an API key is configured
    if OPENWEATHER_API_KEY:
        owm_url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={encoded_city}&appid={OPENWEATHER_API_KEY}&units=metric"
        )
        log_event("skill", "external_service", "openweather_request", {"url": owm_url, "city": clean_city})
        try:
            req = urllib.request.Request(owm_url, headers={"User-Agent": "skill_AI_agent/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            log_event("external_service", "skill", "openweather_response", data)
            return {
                "city": data.get("name", clean_city),
                "temperature_c": data.get("main", {}).get("temp"),
                "feels_like_c": data.get("main", {}).get("feels_like"),
                "condition": (data.get("weather") or [{}])[0].get("description", "Unknown"),
                "humidity_percent": data.get("main", {}).get("humidity"),
                "wind_speed": f"{data.get('wind', {}).get('speed', 'N/A')} m/s",
            }
        except Exception as err:
            log_event("skill", "agent", "openweather_fallback", {"error": str(err)})

    # 2. Fallback to wttr.in JSON format (free, no API key required)
    wttr_url = f"https://wttr.in/{encoded_city}?format=j1"
    log_event("skill", "external_service", "wttr_request", {"url": wttr_url, "city": clean_city})
    try:
        req = urllib.request.Request(wttr_url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        log_event("external_service", "skill", "wttr_response", {"status": "success"})
        curr = data["current_condition"][0]
        desc = curr.get("weatherDesc", [{}])[0].get("value", "Clear")
        return {
            "city": clean_city.title(),
            "temperature_c": curr.get("temp_C"),
            "feels_like_c": curr.get("FeelsLikeC"),
            "condition": desc,
            "humidity_percent": curr.get("humidity"),
            "wind_speed": f"{curr.get('windspeedKmph')} km/h",
        }
    except Exception as err:
        log_event("external_service", "skill", "weather_error", {"error": str(err)})
        return {"error": f"Unable to fetch weather information for '{clean_city}': {err}"}


def get_local_time(city: str) -> dict[str, Any]:
    """Retrieve the current local time and date for a specified city (via skill.md)."""
    clean_city = city.strip().lower()
    tz_name = CITY_TIMEZONES.get(clean_city)

    # If not in local table, try worldtimeapi.org lookup
    if not tz_name:
        for known_city, known_tz in CITY_TIMEZONES.items():
            if known_city in clean_city or clean_city in known_city:
                tz_name = known_tz
                break

    if tz_name:
        try:
            tz = zoneinfo.ZoneInfo(tz_name)
            now = datetime.datetime.now(tz)
            result = {
                "city": city.strip().title(),
                "local_time": now.strftime("%I:%M:%S %p"),
                "local_date": now.strftime("%Y-%m-%d"),
                "timezone": tz_name,
                "utc_offset": now.strftime("%z"),
            }
            log_event("skill", "agent", "local_time_resolved", result)
            return result
        except Exception as err:
            log_event("skill", "agent", "timezone_resolution_error", {"error": str(err)})

    # Fallback attempt via WorldTimeAPI
    wta_url = f"https://worldtimeapi.org/api/timezone/{urllib.parse.quote(tz_name or clean_city)}"
    log_event("skill", "external_service", "worldtime_request", {"url": wta_url})
    try:
        req = urllib.request.Request(wta_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        log_event("external_service", "skill", "worldtime_response", data)
        return {
            "city": city.strip().title(),
            "local_time": data.get("datetime", "")[11:19],
            "local_date": data.get("datetime", "")[:10],
            "timezone": data.get("timezone"),
            "utc_offset": data.get("utc_offset"),
        }
    except Exception as err:
        log_event("external_service", "skill", "time_error", {"error": str(err)})
        return {"error": f"No timezone information available for city '{city}'."}


# -----------------------------------------------------------------------------
# Private House Information Tool
# -----------------------------------------------------------------------------
PRIVATE_HOUSE_DATA = {
    "house_color": "blue",
    "house_city": "San Jose",
}


def get_private_house_information(question: str) -> dict[str, str]:
    """Retrieve private information regarding the user's house (color or city)."""
    q = question.lower()
    has_color = any(w in q for w in ("color", "colour", "paint"))
    has_city = any(w in q for w in ("city", "location", "located", "where", "town"))

    if has_color and has_city:
        return {
            "house_color": PRIVATE_HOUSE_DATA["house_color"],
            "house_city": PRIVATE_HOUSE_DATA["house_city"],
            "answer": (
                f"The house is {PRIVATE_HOUSE_DATA['house_color']} and is located in "
                f"{PRIVATE_HOUSE_DATA['house_city']}."
            ),
        }
    if has_color:
        return {
            "house_color": PRIVATE_HOUSE_DATA["house_color"],
            "answer": f"The house color is {PRIVATE_HOUSE_DATA['house_color']}.",
        }
    if has_city:
        return {
            "house_city": PRIVATE_HOUSE_DATA["house_city"],
            "answer": f"The house is located in {PRIVATE_HOUSE_DATA['house_city']}.",
        }

    return {
        "answer": (
            "I can provide private information only about the house color (blue) "
            "or the city where the house is located (San Jose)."
        )
    }


# -----------------------------------------------------------------------------
# Gemini Tool Declarations & Dispatcher
# -----------------------------------------------------------------------------
SKILL_TOOLS_DECLARATION = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_weather",
            description="Get current weather metrics for a specified city using the active weather skill.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "city": types.Schema(
                        type=types.Type.STRING,
                        description="The city name to retrieve weather for.",
                    )
                },
                required=["city"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_local_time",
            description="Get the current local time and date for a specified city using the active time skill.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "city": types.Schema(
                        type=types.Type.STRING,
                        description="The city name to retrieve local time for.",
                    )
                },
                required=["city"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_private_house_information",
            description="Answer private questions about the user's house (house color: blue, city: San Jose).",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "question": types.Schema(
                        type=types.Type.STRING,
                        description="The user's question regarding their house.",
                    )
                },
                required=["question"],
            ),
        ),
    ]
)

TOOL_MAP = {
    "get_weather": get_weather,
    "get_local_time": get_local_time,
    "get_private_house_information": get_private_house_information,
}


def extract_response_text(response: Any) -> str | None:
    """Extract plain text from candidate response, avoiding SDK warnings on tool calls."""
    try:
        if not response.candidates:
            return None
        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            return None
        texts = [p.text for p in candidate.content.parts if getattr(p, "text", None) and not getattr(p, "thought", False)]
        if not texts:
            texts = [p.text for p in candidate.content.parts if getattr(p, "text", None)]
        return "".join(texts).strip() if texts else None
    except Exception:
        return None


def describe_tools(tool_declaration: types.Tool) -> list[dict[str, Any]]:
    """Format function declarations for clear human-readable logging."""
    return [
        {
            "name": decl.name,
            "description": decl.description,
            "parameters": to_serializable(decl.parameters),
        }
        for decl in (tool_declaration.function_declarations or [])
    ]


# -----------------------------------------------------------------------------
# Agent Turn Execution
# -----------------------------------------------------------------------------
def run_agent_turn(client: genai.Client, user_query: str, model_name: str) -> str:
    """Execute a single agent turn with Gemini, adhering to skill.md instructions."""
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part.from_text(text=user_query)])
    ]
    system_instruction = (
        "You are a helpful and intelligent AI assistant. You answer questions and provide recommendations.\n"
        "You follow the instructions in skill.md to answer questions about weather and local time for any city.\n"
        "You use the get_private_house_information tool to answer questions about the user's house.\n\n"
        f"Active Skill Instructions:\n{SKILL_INSTRUCTIONS}"
    )
    config = types.GenerateContentConfig(
        tools=[SKILL_TOOLS_DECLARATION],
        system_instruction=system_instruction,
        temperature=0.7,
    )

    max_tool_iterations = 6
    for iteration in range(max_tool_iterations):
        log_event(
            sender="agent",
            recipient="llm",
            message_type="generate_content_request",
            payload={
                "iteration": iteration + 1,
                "model": model_name,
                "system_instruction": system_instruction,
                "tools": describe_tools(SKILL_TOOLS_DECLARATION),
                "contents": to_serializable(contents),
            },
        )

        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )

        function_calls = response.function_calls or []
        resp_text = extract_response_text(response)

        log_event(
            sender="llm",
            recipient="agent",
            message_type="generate_content_response",
            payload={
                "iteration": iteration + 1,
                "text": resp_text,
                "function_calls": [
                    {"name": fc.name, "args": fc.args} for fc in function_calls
                ],
            },
        )

        # If no tool calls requested, return final text
        if not function_calls:
            final_text = resp_text or "I am sorry, I could not generate a response."
            return final_text.strip()

        # Add model's intermediate candidate content
        if response.candidates and response.candidates[0].content:
            contents.append(response.candidates[0].content)

        tool_response_parts = []
        for fc in function_calls:
            func_name = fc.name
            func_args = fc.args or {}
            log_event(
                sender="agent",
                recipient=f"skill_or_tool:{func_name}",
                message_type="tool_call",
                payload={"arguments": func_args},
            )

            if func_name in TOOL_MAP:
                tool_result = TOOL_MAP[func_name](**func_args)
            else:
                tool_result = {"error": f"Tool '{func_name}' is not recognized."}

            log_event(
                sender=f"skill_or_tool:{func_name}",
                recipient="agent",
                message_type="tool_response",
                payload={"result": tool_result},
            )

            tool_response_parts.append(
                types.Part.from_function_response(
                    name=func_name,
                    response=tool_result,
                )
            )

        contents.append(types.Content(role="user", parts=tool_response_parts))

    return "Agent reached maximum tool iterations without producing a final answer."


def ask_gemini(client: genai.Client, user_query: str) -> str:
    """Send query to Gemini with fallback model support."""
    models_to_try = [MODEL_NAME]
    if FALLBACK_MODEL_NAME and FALLBACK_MODEL_NAME != MODEL_NAME:
        models_to_try.append(FALLBACK_MODEL_NAME)

    last_error: Exception | None = None
    for model in models_to_try:
        try:
            return run_agent_turn(client, user_query, model)
        except Exception as err:
            last_error = err
            log_event(
                sender="agent",
                recipient="system",
                message_type="model_error",
                payload={"model": model, "error": str(err)},
            )
            print(f"[!] Warning: Model '{model}' failed: {err}. Trying next available model...")

    return f"Error communicating with AI models: {last_error}"


# -----------------------------------------------------------------------------
# Main Interaction Loop
# -----------------------------------------------------------------------------
def main() -> None:
    client = genai.Client(api_key=API_KEY)
    print("=" * 60)
    print("        Skill AI Agent (Weather, Time & Gemini)        ")
    print("=" * 60)
    print("Ask about weather or local time in any city (e.g. 'Weather in Paris?'),")
    print("ask general questions/recommendations, or ask about your house.")
    print("Type 'quit' or 'exit' to end.\n")

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

        # Log prompt marker
        log_prompt(user_input)

        # Process through agent
        response = ask_gemini(client, user_input)

        # Log agent's final output to user
        log_event(
            sender="agent",
            recipient="user",
            message_type="final_response",
            payload={"response": response},
        )

        print(f"\nAgent: {response}\n")


if __name__ == "__main__":
    main()
