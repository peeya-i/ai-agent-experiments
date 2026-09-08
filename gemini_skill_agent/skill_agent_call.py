#!/usr/bin/env python3
"""Skill Agent Call

Implements a terminal AI agent that accepts natural language input, utilizes the
`Agent` class from `google.adk.agents` with tools passed in the `tools` parameter,
orchestrates multiple modular skills (weather skill, local time skill, and house info skill),
references `skill_2.md` for weather and local time lookup, and logs all message exchanges
to `skill_agent_call.log` with human-readable formatting and API keys masked.
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
from typing import Any, Callable

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.runners import InMemoryRunner
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

SKILL_2_FILE = BASE_DIR / "skill_2.md"
SKILL_FILE = BASE_DIR / "skill.md"
LOG_FILE = BASE_DIR / "skill_agent_call.log"

if not API_KEY:
    print("[!] Error: GOOGLE_API_KEY is not set. Please configure it in .env or environment.")
    sys.exit(1)


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
    logger = logging.getLogger("skill_agent_call")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    masking_filter = ApiKeyMaskingFilter()

    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
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
# Modular Skills & Tool Definitions
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
    """Retrieve current weather observation for a specified city (temperature, condition, humidity, wind)."""
    log_event("agent", "skill:weather", "tool_call", {"city": city})
    clean_city = city.strip()
    encoded_city = urllib.parse.quote(clean_city)

    # 1. OpenWeatherMap if configured
    if OPENWEATHER_API_KEY:
        owm_url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={encoded_city}&appid={OPENWEATHER_API_KEY}&units=metric"
        )
        log_event("skill:weather", "external_service", "openweather_request", {"url": owm_url, "city": clean_city})
        try:
            req = urllib.request.Request(owm_url, headers={"User-Agent": "skill_agent_call/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            log_event("external_service", "skill:weather", "openweather_response", data)
            result = {
                "city": data.get("name", clean_city),
                "temperature_c": data.get("main", {}).get("temp"),
                "feels_like_c": data.get("main", {}).get("feels_like"),
                "condition": (data.get("weather") or [{}])[0].get("description", "Unknown"),
                "humidity_percent": data.get("main", {}).get("humidity"),
                "wind_speed": f"{data.get('wind', {}).get('speed', 'N/A')} m/s",
            }
            log_event("skill:weather", "agent", "tool_response", result)
            return result
        except Exception as err:
            log_event("skill:weather", "agent", "openweather_fallback", {"error": str(err)})

    # 2. wttr.in fallback (free, no API key needed)
    wttr_url = f"https://wttr.in/{encoded_city}?format=j1"
    log_event("skill:weather", "external_service", "wttr_request", {"url": wttr_url, "city": clean_city})
    try:
        req = urllib.request.Request(wttr_url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        log_event("external_service", "skill:weather", "wttr_response", {"status": "success"})
        curr = data["current_condition"][0]
        desc = curr.get("weatherDesc", [{}])[0].get("value", "Clear")
        result = {
            "city": clean_city.title(),
            "temperature_c": curr.get("temp_C"),
            "feels_like_c": curr.get("FeelsLikeC"),
            "condition": desc,
            "humidity_percent": curr.get("humidity"),
            "wind_speed": f"{curr.get('windspeedKmph')} km/h",
        }
        log_event("skill:weather", "agent", "tool_response", result)
        return result
    except Exception as err:
        log_event("external_service", "skill:weather", "weather_error", {"error": str(err)})
        err_res = {"error": f"Unable to fetch weather information for '{clean_city}': {err}"}
        log_event("skill:weather", "agent", "tool_response", err_res)
        return err_res


def get_local_time(city: str) -> dict[str, Any]:
    """Retrieve current local time, date, and timezone for a specified city."""
    log_event("agent", "skill:local_time", "tool_call", {"city": city})
    clean_city = city.strip().lower()
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
            result = {
                "city": city.strip().title(),
                "local_time": now.strftime("%I:%M:%S %p"),
                "local_date": now.strftime("%Y-%m-%d"),
                "timezone": tz_name,
                "utc_offset": now.strftime("%z"),
            }
            log_event("skill:local_time", "agent", "tool_response", result)
            return result
        except Exception as err:
            log_event("skill:local_time", "agent", "timezone_error", {"error": str(err)})

    # Fallback to WorldTimeAPI
    wta_url = f"https://worldtimeapi.org/api/timezone/{urllib.parse.quote(tz_name or clean_city)}"
    log_event("skill:local_time", "external_service", "worldtime_request", {"url": wta_url})
    try:
        req = urllib.request.Request(wta_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        log_event("external_service", "skill:local_time", "worldtime_response", data)
        result = {
            "city": city.strip().title(),
            "local_time": data.get("datetime", "")[11:19],
            "local_date": data.get("datetime", "")[:10],
            "timezone": data.get("timezone"),
            "utc_offset": data.get("utc_offset"),
        }
        log_event("skill:local_time", "agent", "tool_response", result)
        return result
    except Exception as err:
        log_event("external_service", "skill:local_time", "time_error", {"error": str(err)})
        err_res = {"error": f"No timezone information available for city '{city}'."}
        log_event("skill:local_time", "agent", "tool_response", err_res)
        return err_res


PRIVATE_HOUSE_DATA = {
    "house_color": "blue",
    "house_city": "San Jose",
}


def get_private_house_information(question: str) -> dict[str, str]:
    """Retrieve private information regarding the user's house (color: blue, city: San Jose)."""
    log_event("agent", "skill:private_house", "tool_call", {"question": question})
    q = question.lower()
    has_color = any(w in q for w in ("color", "colour", "paint"))
    has_city = any(w in q for w in ("city", "location", "located", "where", "town"))

    if has_color and has_city:
        result = {
            "house_color": PRIVATE_HOUSE_DATA["house_color"],
            "house_city": PRIVATE_HOUSE_DATA["house_city"],
            "answer": (
                f"The house is {PRIVATE_HOUSE_DATA['house_color']} and is located in "
                f"{PRIVATE_HOUSE_DATA['house_city']}."
            ),
        }
    elif has_color:
        result = {
            "house_color": PRIVATE_HOUSE_DATA["house_color"],
            "answer": f"The house color is {PRIVATE_HOUSE_DATA['house_color']}.",
        }
    elif has_city:
        result = {
            "house_city": PRIVATE_HOUSE_DATA["house_city"],
            "answer": f"The house is located in {PRIVATE_HOUSE_DATA['house_city']}.",
        }
    else:
        result = {
            "answer": (
                "I can provide private information only about the house color (blue) "
                "or the city where the house is located (San Jose)."
            )
        }

    log_event("skill:private_house", "agent", "tool_response", result)
    return result


# -----------------------------------------------------------------------------
# Multiple Skills Registry
# -----------------------------------------------------------------------------
@dataclass
class SkillModule:
    name: str
    description: str
    instructions: str
    tools: list[Callable[..., Any]]


def load_skill_reference() -> str:
    """Load skill instructions from skill_2.md or skill.md."""
    for path in (SKILL_2_FILE, SKILL_FILE):
        if path.exists():
            return path.read_text(encoding="utf-8")
    return ""


SKILL_2_CONTENT = load_skill_reference()

WEATHER_SKILL = SkillModule(
    name="weather_skill",
    description="Skill to fetch current weather conditions in any city.",
    instructions=(
        "Use 'get_weather(city)' to answer questions regarding current weather in a city. "
        "Summarize temperature in Celsius, weather conditions, humidity, and wind."
    ),
    tools=[get_weather],
)

LOCAL_TIME_SKILL = SkillModule(
    name="local_time_skill",
    description="Skill to fetch accurate local time and date for any city.",
    instructions=(
        "Use 'get_local_time(city)' to answer questions about the current local time in a city. "
        "Report the formatted time, date, timezone, and UTC offset."
    ),
    tools=[get_local_time],
)

HOUSE_INFO_SKILL = SkillModule(
    name="house_info_skill",
    description="Skill to answer private questions about the user's house.",
    instructions=(
        "Use 'get_private_house_information(question)' whenever the user asks about the color "
        "or city location of their house (house color: blue, location: San Jose)."
    ),
    tools=[get_private_house_information],
)

# Used as multiple modular skills in the code
SKILLS: list[SkillModule] = [WEATHER_SKILL, LOCAL_TIME_SKILL, HOUSE_INFO_SKILL]


# -----------------------------------------------------------------------------
# Agent Invocation with google.adk.agents.Agent
# -----------------------------------------------------------------------------
def build_agent_instruction() -> str:
    """Build overall instruction incorporating all active skills and skill_2.md."""
    sections = [
        "You are a helpful and intelligent AI assistant. You answer questions and provide recommendations.",
        "You follow the instructions in skill_2.md to answer questions about weather and local time for any city.",
        "You use get_private_house_information to answer questions about the user's house.",
    ]
    if SKILL_2_CONTENT:
        sections.append(f"\nActive Skill Reference (skill_2.md):\n{SKILL_2_CONTENT}")

    sections.append("\nRegistered Active Skills:")
    for skill in SKILLS:
        sections.append(f"- {skill.name}: {skill.description}\n  {skill.instructions}")

    return "\n".join(sections)


def create_adk_agent(
    model_name: str,
    tools: list[Callable[..., Any]],
    instruction: str,
) -> Agent:
    """Instantiate the AI Agent using the Agent method from google.adk.agents."""
    return Agent(
        name="skill_gemini_agent",
        model=Gemini(model=model_name),
        tools=tools,  # Tools passed in the tools parameter
        instruction=instruction,
    )


class AgentTurnManager:
    """Manages conversational turns, model fallback, and execution via ADK Runner."""

    def __init__(
        self,
        tools: list[Callable[..., Any]],
        instruction: str,
        primary_model: str = MODEL_NAME,
        fallback_model: str | None = FALLBACK_MODEL_NAME,
    ) -> None:
        self.tools = tools
        self.instruction = instruction
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.active_model = primary_model

        # Create primary Agent using google.adk.agents.Agent
        self.agent = create_adk_agent(self.active_model, self.tools, self.instruction)
        self.runner = InMemoryRunner(agent=self.agent)
        self.user_id = "terminal_user"
        self.session_id = f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.runner.session_service.create_session_sync(
            user_id=self.user_id,
            session_id=self.session_id,
            app_name=self.runner.app_name,
        )

    def _switch_to_fallback(self) -> None:
        if not self.fallback_model or self.active_model == self.fallback_model:
            return
        log_event(
            "agent",
            "system",
            "model_fallback",
            {"from": self.active_model, "to": self.fallback_model},
        )
        print(f"[!] Falling back to model: {self.fallback_model}")
        self.active_model = self.fallback_model
        self.agent = create_adk_agent(self.active_model, self.tools, self.instruction)
        self.runner = InMemoryRunner(agent=self.agent)
        self.session_id = f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.runner.session_service.create_session_sync(
            user_id=self.user_id,
            session_id=self.session_id,
            app_name=self.runner.app_name,
        )

    def execute_turn(self, user_query: str) -> str:
        """Run a turn with the google.adk.agents.Agent, logging all message flows."""
        # Log outgoing LLM request
        tool_names = [getattr(t, "__name__", str(t)) for t in self.tools]
        log_event(
            sender="agent",
            recipient="llm",
            message_type="adk_agent_request",
            payload={
                "model": self.active_model,
                "instruction": self.instruction,
                "tools": tool_names,
                "user_message": user_query,
            },
        )

        try:
            return self._run_runner_loop(user_query)
        except Exception as err:
            log_event(
                sender="llm",
                recipient="agent",
                message_type="model_error",
                payload={"model": self.active_model, "error": str(err)},
            )
            if self.fallback_model and self.active_model != self.fallback_model:
                self._switch_to_fallback()
                return self._run_runner_loop(user_query)
            return f"Error running agent turn: {err}"

    def _run_runner_loop(self, user_query: str) -> str:
        new_content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_query)],
        )

        events = list(
            self.runner.run(
                user_id=self.user_id,
                session_id=self.session_id,
                new_message=new_content,
            )
        )

        final_response_text = ""
        for event in events:
            if not event.content or not event.content.parts:
                continue

            for part in event.content.parts:
                # Log model function calls
                func_call = getattr(part, "function_call", None)
                if func_call:
                    log_event(
                        sender="llm",
                        recipient="agent",
                        message_type="function_call_requested",
                        payload={"name": func_call.name, "args": func_call.args},
                    )

                # Capture final text parts from model
                text = getattr(part, "text", None)
                if text and not getattr(part, "thought", False):
                    final_response_text += text

        if not final_response_text:
            # Fallback check for text if not separated from thoughts
            for event in reversed(events):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if getattr(part, "text", None):
                            final_response_text = part.text
                            break
                    if final_response_text:
                        break

        clean_response = final_response_text.strip() or "I am sorry, I could not generate an answer."
        log_event(
            sender="llm",
            recipient="agent",
            message_type="adk_agent_response",
            payload={"response_text": clean_response},
        )
        return clean_response


# -----------------------------------------------------------------------------
# Main Interaction Loop
# -----------------------------------------------------------------------------
def main() -> None:
    # 1. Collect all tools across multiple skills
    tools: list[Callable[..., Any]] = []
    for skill in SKILLS:
        tools.extend(skill.tools)

    # 2. Build overall instructions from skills & skill_2.md
    instruction = build_agent_instruction()

    # 3. Create agent turn manager utilizing google.adk.agents.Agent
    agent_manager = AgentTurnManager(
        tools=tools,  # Passed in the tools parameter
        instruction=instruction,
        primary_model=MODEL_NAME,
        fallback_model=FALLBACK_MODEL_NAME,
    )

    print("=" * 60)
    print("   Skill Agent Call (google.adk.agents.Agent & Skills)   ")
    print("=" * 60)
    print("Ask about weather, local time, recommendations, or your house.")
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

        # Run turn with Agent
        response = agent_manager.execute_turn(user_input)

        # Log final response to user
        log_event(
            sender="agent",
            recipient="user",
            message_type="final_response",
            payload={"response": response},
        )

        print(f"\nAgent: {response}\n")


if __name__ == "__main__":
    main()
