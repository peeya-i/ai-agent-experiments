import logging
import sys
from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest


def setup_logging(
    level: int = logging.INFO,
    log_format: Optional[str] = None,
    stream: Optional[sys.stdout] = None,
) -> None:
    """Configures local Python logging to replace Google Cloud Logging.

    Ensures INFO-level logs from ADK callbacks and agent workflows are visible
    in the console/terminal without requiring Google Cloud credentials or
    external cloud logging services.
    """
    if log_format is None:
        log_format = "%(asctime)s [%(levelname)s] %(message)s"

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Check if a StreamHandler already exists
    has_stream_handler = any(
        isinstance(h, logging.StreamHandler) for h in root_logger.handlers
    )

    if not has_stream_handler:
        handler = logging.StreamHandler(stream or sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(log_format, datefmt="%H:%M:%S"))
        root_logger.addHandler(handler)
    else:
        # Update existing handlers to ensure the log level and format are active
        for h in root_logger.handlers:
            h.setLevel(level)
            if not h.formatter:
                h.setFormatter(logging.Formatter(log_format, datefmt="%H:%M:%S"))


def log_query_to_model(callback_context: CallbackContext, llm_request: LlmRequest) -> None:
    """Callback before sending request to model. Logs the user's prompt."""
    agent_name = getattr(callback_context, "agent_name", "unknown_agent")
    if llm_request and llm_request.contents:
        last_content = llm_request.contents[-1]
        if getattr(last_content, "role", None) == "user":
            for part in getattr(last_content, "parts", []):
                text = getattr(part, "text", None)
                if text:
                    logging.info("[query to %s]: %s", agent_name, text)


def log_model_response(callback_context: CallbackContext, llm_response: LlmResponse) -> None:
    """Callback after receiving response from model. Logs model text or function call."""
    agent_name = getattr(callback_context, "agent_name", "unknown_agent")
    if llm_response and llm_response.content:
        for part in getattr(llm_response.content, "parts", []):
            text = getattr(part, "text", None)
            func_call = getattr(part, "function_call", None)
            if text:
                logging.info("[response from %s]: %s", agent_name, text)
            elif func_call:
                name = getattr(func_call, "name", "unknown_func")
                logging.info("[function call from %s]: %s", agent_name, name)
