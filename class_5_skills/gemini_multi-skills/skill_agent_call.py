#!/usr/bin/env python3
"""Skill Agent Call (Multi-Skill AI Agent)

Implements a terminal AI agent that accepts natural language input, utilizes the
`Agent` method from `google.adk.agents` with tools passed in the `tools` parameter,
supports LLM skill selection and multi-step reasoning across multiple skills
(skill_1: weather and local time; skill_2: house information), provides general
recommendations and answers, and logs all message flows to `multi-skill_agent.log`
with security-masked API keys.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import sys
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

# Suppress experimental / deprecation warnings from underlying frameworks
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# -----------------------------------------------------------------------------
# Configuration & Environment
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("GOOGLE_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
MODEL_NAME = os.getenv("MODEL", "gemma-4-26b-a4b-it")
FALLBACK_MODEL_NAME = os.getenv("FALLBACK_MODEL", "gemini-3.5-flash-lite")
LOG_FILE = BASE_DIR / "multi-skill_agent.log"

if not API_KEY:
    print("[!] Error: GOOGLE_API_KEY is not set. Please configure it in .env or environment.")
    sys.exit(1)

# Ensure current directory is on sys.path so skill modules are found
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# -----------------------------------------------------------------------------
# Logging Infrastructure (from logging.py per multi-skill_agent.yaml)
# -----------------------------------------------------------------------------
# Import the logging code from logging.py that is called from the main program
from logging import (
    ApiKeyMaskingFilter,
    LogEvent,
    log_event,
    log_prompt,
    setup_agent_logger,
    to_serializable,
)


# -----------------------------------------------------------------------------
# Google ADK Imports & Skill Tools Wiring
# -----------------------------------------------------------------------------
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.runners import InMemoryRunner
from google.genai import types

import skill_1.tools
import skill_2.tools
from skill_1.tools import get_local_time, get_weather
from skill_2.tools import get_house_city, get_house_color, get_private_house_information

# Register logger callback with skill tools
skill_1.tools.set_logger(log_event)
skill_2.tools.set_logger(log_event)


# -----------------------------------------------------------------------------
# Skill Selection Tool (Allows LLM to inspect and select active skills)
# -----------------------------------------------------------------------------
def select_skill(skill_name: str) -> dict[str, Any]:
    """Select and activate a skill by name to inspect its instructions and tools.

    Args:
        skill_name: 'skill_1' (for weather & local time) or 'skill_2' (for house questions).
    """
    log_event("agent", f"skill_selector:{skill_name}", "tool_request", {"skill_name": skill_name})
    clean = skill_name.strip().lower()

    if "1" in clean or "weather" in clean or "time" in clean:
        skill_file = BASE_DIR / "skill_1" / "skill_1.md"
        doc = skill_file.read_text(encoding="utf-8") if skill_file.exists() else ""
        result = {
            "selected_skill": "skill_1",
            "name": "city_weather_and_local_time",
            "description": "Handles weather conditions and local time for any city worldwide.",
            "available_tools": ["get_weather", "get_local_time"],
            "procedure_summary": (
                "Call get_weather(city) for weather metrics. "
                "Call get_local_time(city) for local time/timezone. "
                "Tools are located in the skill_1 folder."
            ),
        }
    elif "2" in clean or "house" in clean or "home" in clean:
        skill_file = BASE_DIR / "skill_2" / "skill_2.md"
        doc = skill_file.read_text(encoding="utf-8") if skill_file.exists() else ""
        result = {
            "selected_skill": "skill_2",
            "name": "user_house_information",
            "description": "Answers private questions about the user's house.",
            "available_tools": [
                "get_house_color",
                "get_house_city",
                "get_private_house_information",
            ],
            "facts": {
                "house_color": "blue",
                "house_city": "San Jose",
            },
            "procedure_summary": (
                "Call get_house_color() to get the house color (blue). "
                "Call get_house_city() to get the house city (San Jose). "
                "Call get_private_house_information(question) for compound questions. "
                "Tools are located in the skill_2 folder."
            ),
        }
    else:
        result = {
            "selected_skill": skill_name,
            "error": (
                f"Unknown skill '{skill_name}'. Available skills are 'skill_1' "
                "(weather & local time) and 'skill_2' (user house info)."
            ),
        }

    log_event(f"skill_selector:{skill_name}", "agent", "tool_response", result)
    return result


# -----------------------------------------------------------------------------
# Logging Gemini Model (captures actual request & response payloads with LLM)
# -----------------------------------------------------------------------------
from typing import AsyncGenerator
from google.adk.models import LlmRequest, LlmResponse


class LoggingGemini(Gemini):
    """Gemini model adapter that logs the exact request and response payloads exchanged with the LLM."""

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        # Log actual request payload sent from agent to LLM
        req_contents = [to_serializable(c) for c in (llm_request.contents or [])]
        req_tools = (
            [to_serializable(t) for t in (llm_request.config.tools or [])]
            if (llm_request.config and getattr(llm_request.config, "tools", None))
            else None
        )
        req_payload: dict[str, Any] = {
            "model": llm_request.model,
            "contents": req_contents,
        }
        if req_tools:
            req_payload["tools"] = req_tools

        log_event(
            sender="agent",
            recipient="llm",
            message_type="generate_content_request",
            payload=req_payload,
        )

        async for response in super().generate_content_async(llm_request, stream=stream):
            resp_content = to_serializable(getattr(response, "content", None))
            resp_payload: dict[str, Any] = {
                "model_version": getattr(response, "model_version", None),
                "finish_reason": str(getattr(response, "finish_reason", "")),
                "content": resp_content,
            }
            usage = getattr(response, "usage_metadata", None)
            if usage:
                resp_payload["usage_metadata"] = to_serializable(usage)

            log_event(
                sender="llm",
                recipient="agent",
                message_type="generate_content_response",
                payload=resp_payload,
            )
            yield response


# -----------------------------------------------------------------------------
# All Tools List (passed in the tools parameter to Agent)
# -----------------------------------------------------------------------------
ALL_TOOLS: list[Callable[..., Any]] = [
    select_skill,
    get_weather,
    get_local_time,
    get_house_color,
    get_house_city,
    get_private_house_information,
]


# -----------------------------------------------------------------------------
# System Instruction Construction
# -----------------------------------------------------------------------------
def build_agent_instruction() -> str:
    """Build comprehensive agent instructions including multi-skill orchestration."""
    instruction = (
        "You are an intelligent, helpful multi-skill AI Assistant. "
        "You understand natural language input, answer general questions, and provide recommendations.\n\n"
        "You have access to two specialized skills:\n"
        "1. Skill 1 (`city_weather_and_local_time` in folder `skill_1`): "
        "Helps you answer questions about the weather in a specific city and the local time in that city. "
        "Tools: `get_weather(city)`, `get_local_time(city)`.\n"
        "2. Skill 2 (`user_house_information` in folder `skill_2`): "
        "Answers questions about the user's house. "
        "Facts: The color of the house is always blue; the city where the house is located is always San Jose. "
        "Tools: `get_house_color()`, `get_house_city()`, `get_private_house_information(question)`.\n\n"
        "SKILL SELECTION & MULTI-STEP REASONING WORKFLOW:\n"
        "- When a user query requires specialized knowledge, you may use `select_skill(skill_name)` "
        "or directly execute the appropriate tool(s).\n"
        "- When answering questions that require multiple steps (for example: "
        "'What is the weather and local time in the city where my house is located?'):\n"
        "   Step 1: Use `get_house_city()` from skill_2 to find the city where the house is located ('San Jose').\n"
        "   Step 2: Use `get_weather(city='San Jose')` and `get_local_time(city='San Jose')` from skill_1 "
        "to retrieve current weather and local time for that city.\n"
        "   Step 3: Combine all details and formulate a clear, comprehensive answer for the user.\n\n"
        "GENERAL TASKS:\n"
        "- For questions not requiring external tools or for recommendation requests (e.g. books, podcasts, movies), "
        "respond directly with helpful, structured recommendations.\n"
    )
    return instruction


# -----------------------------------------------------------------------------
# Agent Turn Manager
# -----------------------------------------------------------------------------
class MultiSkillAgentManager:
    """Manages the Agent lifecycle, ADK InMemoryRunner, fallback models, and logging."""

    def __init__(
        self,
        tools: list[Callable[..., Any]] = ALL_TOOLS,
        primary_model: str = MODEL_NAME,
        fallback_model: str | None = FALLBACK_MODEL_NAME,
    ) -> None:
        self.tools = tools
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.active_model = primary_model
        self.instruction = build_agent_instruction()

        self._init_agent_and_runner()

    def _init_agent_and_runner(self) -> None:
        """Create the Agent instance using google.adk.agents.Agent."""
        # Using the Agent method from google.adk.agents with tools passed in the tools parameter
        self.agent = Agent(
            name="multi_skill_agent",
            model=LoggingGemini(model=self.active_model),
            tools=self.tools,  # Tools passed to the agent in the tools parameter
            instruction=self.instruction,
        )
        self.runner = InMemoryRunner(agent=self.agent)
        self.user_id = "terminal_user"
        self.session_id = f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        self.runner.session_service.create_session_sync(
            user_id=self.user_id,
            session_id=self.session_id,
            app_name=self.runner.app_name,
        )

    def _switch_to_fallback(self) -> None:
        """Switch to fallback model if primary model fails."""
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
        self._init_agent_and_runner()

    def execute_turn(self, user_query: str) -> str:
        """Execute one conversational turn, logging message exchanges between agent, LLM, and tools."""
        try:
            response = self._run_turn_internal(user_query)
            # If primary model returned empty response (e.g. quota limit error caught internally by runner)
            if (not response or "could not generate an answer" in response) and self.fallback_model and self.active_model != self.fallback_model:
                self._switch_to_fallback()
                response = self._run_turn_internal(user_query)
            return response
        except Exception as err:
            log_event(
                sender="llm",
                recipient="agent",
                message_type="model_error",
                payload={"model": self.active_model, "error": str(err)},
            )
            if self.fallback_model and self.active_model != self.fallback_model:
                self._switch_to_fallback()
                return self._run_turn_internal(user_query)
            return f"Error executing turn: {err}"

    def _run_turn_internal(self, user_query: str) -> str:
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
                # Capture final text parts from model (ignoring internal thoughts)
                text = getattr(part, "text", None)
                if text and not getattr(part, "thought", False):
                    final_response_text += text

        # Fallback text extraction if model text was not tagged with thought=False
        if not final_response_text:
            raise RuntimeError(f"Model '{self.active_model}' returned empty response or encountered an error.")

        clean_response = final_response_text.strip()
        return clean_response


# -----------------------------------------------------------------------------
# Terminal Interaction Loop
# -----------------------------------------------------------------------------
def main() -> None:
    print("=" * 60)
    print("      Multi-Skill AI Agent (google.adk.agents.Agent)      ")
    print("=" * 60)
    print("Skills Available:")
    print("  - Skill 1: Weather & Local Time in any city")
    print("  - Skill 2: User House Information (Color: blue, City: San Jose)")
    print("  - General: Questions & Recommendations")
    print("Type 'quit' or 'exit' to end.\n")

    manager = MultiSkillAgentManager(
        tools=ALL_TOOLS,
        primary_model=MODEL_NAME,
        fallback_model=FALLBACK_MODEL_NAME,
    )

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

        # Mark prompt with === PROMPT === in multi-skill_agent.log
        log_prompt(user_input)

        # Run multi-step agent turn
        response = manager.execute_turn(user_input)

        # Log final agent response to user
        log_event(
            sender="agent",
            recipient="user",
            message_type="final_response",
            payload={"response": response},
        )

        print(f"\nAgent: {response}\n")


if __name__ == "__main__":
    main()
