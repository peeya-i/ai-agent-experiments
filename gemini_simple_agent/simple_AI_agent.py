#!/usr/bin/env python3
"""Simple AI Agent

Implements a terminal AI agent that accepts natural language input, invokes Google
Gemini / Gemma models, provides answers and recommendations, uses a private tool
to answer questions about the user's house (color: blue, city: San Jose), and logs
all messages exchanged between agent, LLM, and tools to a structured log file with
API keys masked.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import sys
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
MODEL_NAME = os.getenv("MODEL", "gemma-4-26b-a4b-it")
FALLBACK_MODEL_NAME = os.getenv("FALLBACK_MODEL", "gemini-3.5-flash-lite")

LOG_FILE = BASE_DIR / "simple_AI_agent.log"
ALT_LOG_FILE = BASE_DIR / "ai_agent.log"

if not API_KEY:
    print("[!] Error: GOOGLE_API_KEY is not set. Please add it to .env or environment.")
    sys.exit(1)


# -----------------------------------------------------------------------------
# Logging System
# -----------------------------------------------------------------------------
class ApiKeyMaskingFilter(logging.Filter):
    """Masks the API key anywhere it appears in log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if API_KEY:
            message = message.replace(API_KEY, "[REDACTED_API_KEY]")
        record.msg = message
        record.args = ()
        return True


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("simple_AI_agent")
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
    serializable_payload = to_serializable(payload)
    event = LogEvent(
        sender=sender,
        recipient=recipient,
        message_type=message_type,
        payload=serializable_payload,
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
# Private House Information Tool
# -----------------------------------------------------------------------------
PRIVATE_HOUSE_DATA = {
    "house_color": "blue",
    "house_city": "San Jose",
}


def get_private_house_information(question: str) -> dict[str, str]:
    """Retrieve private information regarding the user's house (color or city)."""
    q = question.lower()
    has_color = any(word in q for word in ("color", "colour", "paint"))
    has_city = any(word in q for word in ("city", "location", "located", "where", "town"))

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


HOUSE_TOOL_DECLARATION = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_private_house_information",
            description=(
                "Answer private questions about the user's house, including the house color "
                "(which is blue) and the city where the house is located (which is San Jose)."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "question": types.Schema(
                        type=types.Type.STRING,
                        description="The specific question or topic regarding the user's house.",
                    )
                },
                required=["question"],
            ),
        )
    ]
)

TOOL_MAP = {
    "get_private_house_information": get_private_house_information,
}


def extract_response_text(response: Any) -> str | None:
    """Safely extract response text without triggering SDK warnings on tool calls."""
    try:
        if not response.candidates:
            return None
        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            return None
        texts = [p.text for p in candidate.content.parts if getattr(p, "text", None) and not getattr(p, "thought", False)]
        if not texts:
            # Fall back to any text parts if non-thought text wasn't separated
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
# Agent Core Logic
# -----------------------------------------------------------------------------
def run_agent_turn(client: genai.Client, user_query: str, model_name: str) -> str:
    """Process a single turn of conversation with Gemini, handling tools if invoked."""
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part.from_text(text=user_query)])
    ]
    system_instruction = (
        "You are a friendly and knowledgeable AI Assistant. You understand natural language, "
        "answer general questions, and provide helpful recommendations. "
        "You also have access to a tool called 'get_private_house_information' to retrieve private "
        "facts about the user's house (such as its color and city location). "
        "Always invoke this tool whenever the user inquires about their house."
    )
    config = types.GenerateContentConfig(
        tools=[HOUSE_TOOL_DECLARATION],
        system_instruction=system_instruction,
        temperature=0.7,
    )

    max_tool_iterations = 5
    for iteration in range(max_tool_iterations):
        log_event(
            sender="agent",
            recipient="llm",
            message_type="generate_content_request",
            payload={
                "iteration": iteration + 1,
                "model": model_name,
                "system_instruction": system_instruction,
                "tools": describe_tools(HOUSE_TOOL_DECLARATION),
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

        # If no tool calls requested, we have the final answer
        if not function_calls:
            final_text = resp_text or "I am sorry, I could not generate an answer."
            return final_text.strip()

        # Add assistant's tool-calling response to conversation contents
        if response.candidates and response.candidates[0].content:
            contents.append(response.candidates[0].content)

        tool_response_parts = []
        for fc in function_calls:
            func_name = fc.name
            func_args = fc.args or {}
            log_event(
                sender="agent",
                recipient=f"tool:{func_name}",
                message_type="tool_call",
                payload={"arguments": func_args},
            )

            if func_name in TOOL_MAP:
                tool_result = TOOL_MAP[func_name](**func_args)
            else:
                tool_result = {"error": f"Tool '{func_name}' is not recognized."}

            log_event(
                sender=f"tool:{func_name}",
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

        # Feed tool execution result back to LLM
        contents.append(types.Content(role="user", parts=tool_response_parts))

    return "Agent reached maximum tool iterations without producing a final answer."


def ask_gemini(client: genai.Client, user_query: str) -> str:
    """Call Gemini with fallback support if primary model encounters an error."""
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
            print(f"[!] Warning: Model '{model}' error: {err}. Trying next model if available...")

    return f"Error communicating with AI models: {last_error}"


# -----------------------------------------------------------------------------
# Main Interaction Loop
# -----------------------------------------------------------------------------
def main() -> None:
    client = genai.Client(api_key=API_KEY)
    print("=" * 60)
    print("           Simple AI Agent (Powered by Gemini)           ")
    print("=" * 60)
    print("Type your questions or requests (e.g. for recommendations).")
    print("Ask about your house, or type 'quit' or 'exit' to end.\n")

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

        # Log prompt line
        log_prompt(user_input)

        # Process query through agent and Gemini
        response = ask_gemini(client, user_input)

        # Log final response delivered to user
        log_event(
            sender="agent",
            recipient="user",
            message_type="final_response",
            payload={"response": response},
        )

        print(f"\nAgent: {response}\n")


if __name__ == "__main__":
    main()
