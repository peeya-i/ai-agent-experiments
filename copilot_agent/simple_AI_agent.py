"""A small terminal-based Gemini agent with one private-house tool."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "simple_AI_agent.log"

load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("GOOGLE_API_KEY", "")
MODEL = os.getenv("MODEL", "gemini-2.5-flash")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gemini-2.5-flash")


class ApiKeyRedactingFilter(logging.Filter):
    """Redact the configured API key anywhere it appears in a log message."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if API_KEY:
            message = message.replace(API_KEY, "[REDACTED_API_KEY]")
        record.msg = message
        record.args = ()
        return True


logger = logging.getLogger("simple_AI_agent")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
handler.addFilter(ApiKeyRedactingFilter())
logger.addHandler(handler)


PRIVATE_HOUSE_DATA = {
    "house_color": "blue",
    "house_city": "San Jose",
}


def get_private_house_information(question: str) -> dict[str, str]:
    """Return the private house fact relevant to a supported question."""
    normalized_question = question.lower()
    if any(word in normalized_question for word in ("color", "colour")):
        return {"answer": PRIVATE_HOUSE_DATA["house_color"]}
    if any(word in normalized_question for word in ("city", "where", "location")):
        return {"answer": PRIVATE_HOUSE_DATA["house_city"]}
    return {"answer": "I can only answer questions about the house color or city."}


HOUSE_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_private_house_information",
            description="Answer a private question about the user's house color or city.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "question": types.Schema(
                        type=types.Type.STRING,
                        description="The user's natural-language question about the house.",
                    )
                },
                required=["question"],
            ),
        )
    ]
)


@dataclass
class InteractionEvent:
    """A message exchanged across one agent boundary."""

    sender: str
    recipient: str
    message_type: str
    payload: Any


def to_loggable(value: Any) -> Any:
    """Convert Gemini SDK objects into readable JSON-compatible values."""
    if hasattr(value, "model_dump"):
        return to_loggable(value.model_dump(exclude_none=True))
    if hasattr(value, "to_json_dict"):
        return to_loggable(value.to_json_dict())
    if isinstance(value, dict):
        return {str(key): to_loggable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_loggable(item) for item in value]
    return value


def log_event(sender: str, recipient: str, message_type: str, payload: Any) -> None:
    event = InteractionEvent(sender, recipient, message_type, payload)
    event_header = f"{sender.upper()} -> {recipient.upper()} [{message_type}]"
    event_payload = json.dumps(
        to_loggable(asdict(event)["payload"]),
        default=str,
        ensure_ascii=False,
        indent=2,
    )
    logger.info("%s\n%s", event_header, event_payload)


def log_prompt(user_input: str) -> None:
    logger.info("=== PROMPT ===")
    log_event("user", "agent", "input", {"text": user_input})


def log_interaction(user_input: str, output: str) -> None:
    log_event("agent", "user", "output", output)


def describe_tools() -> list[dict[str, Any]]:
    """Return the function declarations sent to the LLM in a log-friendly form."""
    return [
        {
            "name": declaration.name,
            "description": declaration.description,
            "parameters": declaration.parameters,
        }
        for declaration in HOUSE_TOOL.function_declarations or []
    ]


def ask_agent(client: genai.Client, user_input: str, model: str) -> str:
    """Send one user request and resolve any Gemini function calls."""
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part.from_text(text=user_input)])
    ]
    config = types.GenerateContentConfig(
        tools=[HOUSE_TOOL],
        system_instruction=(
            "You are a helpful terminal assistant. Answer questions and provide "
            "recommendations. Use get_private_house_information whenever the user "
            "asks about the color or city of their house."
        ),
    )

    for _ in range(5):
        log_event(
            "agent",
            "llm",
            "request",
            {
                "model": model,
                "system_instruction": config.system_instruction,
                "available_tools": describe_tools(),
                "contents": to_loggable(contents),
            },
        )
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        log_event(
            "llm",
            "agent",
            "response",
            {
                "text": response.text,
                "function_calls": [
                    {"name": call.name, "args": call.args}
                    for call in (response.function_calls or [])
                ],
                "response_details": to_loggable(response),
            },
        )
        function_calls = response.function_calls or []
        if not function_calls:
            return response.text or "I could not produce a response."

        contents.append(response.candidates[0].content)
        function_parts = []
        for function_call in function_calls:
            arguments = function_call.args or {}
            log_event("agent", "tool", function_call.name, arguments)
            result = get_private_house_information(arguments.get("question", ""))
            log_event("tool", "agent", function_call.name, result)
            function_parts.append(
                types.Part.from_function_response(
                    name=function_call.name,
                    response=result,
                )
            )
        contents.append(types.Content(role="user", parts=function_parts))

    raise RuntimeError("The model requested too many tool calls.")


def main() -> None:
    if not API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not set. Add it to .env or the environment.")

    client = genai.Client(api_key=API_KEY)
    model = MODEL
    print("Simple Gemini AI agent. Type 'quit' or 'exit' to stop.")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit"}:
            break

        try:
            log_prompt(user_input)
            try:
                output = ask_agent(client, user_input, model)
            except Exception as first_error:
                if model == FALLBACK_MODEL:
                    raise
                logger.info("primary_model_error=%s", first_error)
                model = FALLBACK_MODEL
                output = ask_agent(client, user_input, model)
            print(f"Agent: {output}")
            log_interaction(user_input, output)
        except Exception as error:
            output = f"I could not complete that request: {error}"
            print(f"Agent: {output}")
            log_event("agent", "user", "error", output)


if __name__ == "__main__":
    main()
