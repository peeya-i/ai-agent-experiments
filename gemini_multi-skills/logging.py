"""Logging module for Multi-Skill AI Agent.

Implements structured logging to multi-skill_agent.log, masks API keys for
security, marks each prompt with "=== PROMPT ===", logs actual requests and
responses payload exchanged between agent, LLM, tools, and skills, and safely
proxies standard library logging symbols so third-party dependencies (such as
google.adk and google.genai) operate seamlessly.
"""

from __future__ import annotations

import datetime
import importlib.util
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# -----------------------------------------------------------------------------
# Standard Library Logging Proxy Setup
# -----------------------------------------------------------------------------
_current_dir = Path(__file__).resolve().parent
_candidate = None
for _p in sys.path:
    if _p:
        try:
            if Path(_p).resolve() != _current_dir:
                _c = Path(_p) / "logging" / "__init__.py"
                if _c.exists():
                    _candidate = str(_c)
                    break
        except Exception:
            continue

if _candidate:
    __path__ = [str(Path(_candidate).parent)]
    _spec = importlib.util.spec_from_file_location("logging", _candidate)
    if _spec and _spec.loader:
        _stdlib = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_stdlib)
        globals().update(
            {k: getattr(_stdlib, k) for k in dir(_stdlib) if not k.startswith("__")}
        )
        _Filter = getattr(_stdlib, "Filter")
        _Formatter = getattr(_stdlib, "Formatter")
        _FileHandler = getattr(_stdlib, "FileHandler")
        _getLogger = getattr(_stdlib, "getLogger")
        _INFO = getattr(_stdlib, "INFO")
else:
    import logging as _stdlib  # type: ignore
    _Filter = _stdlib.Filter
    _Formatter = _stdlib.Formatter
    _FileHandler = _stdlib.FileHandler
    _getLogger = _stdlib.getLogger
    _INFO = _stdlib.INFO

# -----------------------------------------------------------------------------
# Configuration & Paths
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "multi-skill_agent.log"

# Retrieve API keys to mask
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")


# -----------------------------------------------------------------------------
# API Key Masking Filter
# -----------------------------------------------------------------------------
class ApiKeyMaskingFilter(_Filter):
    """Filter that intercepts and masks API keys anywhere they appear in log records."""

    def filter(self, record: Any) -> bool:
        message = record.getMessage()

        # Mask explicit environment API keys
        for key in (GOOGLE_API_KEY, OPENWEATHER_API_KEY):
            if key and len(key) > 5:
                message = message.replace(key, "[REDACTED_API_KEY]")

        # Pattern-based masking for Google API keys (AIza...) and generic auth tokens
        message = re.sub(r"AIza[0-9A-Za-z-_]{35}", "[REDACTED_GOOGLE_API_KEY]", message)
        message = re.sub(
            r'(?i)(key|token|secret|password|appid|api_key)["\']?\s*[:=]\s*["\']([a-zA-Z0-9_\-]{16,})["\']',
            r'\1: "[REDACTED_KEY]"',
            message,
        )
        record.msg = message
        record.args = ()
        return True


# -----------------------------------------------------------------------------
# Logger Initialization
# -----------------------------------------------------------------------------
def setup_agent_logger(log_file: Path | str = LOG_FILE) -> Any:
    """Initialize and configure the multi-skill agent logger."""
    logger = _getLogger("multi_skill_agent")
    logger.setLevel(_INFO)
    logger.handlers.clear()

    formatter = _Formatter("%(asctime)s [%(levelname)s] %(message)s")
    masking_filter = ApiKeyMaskingFilter()

    handler = _FileHandler(str(log_file), encoding="utf-8", mode="a")
    handler.setFormatter(formatter)
    handler.addFilter(masking_filter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger


agent_logger = setup_agent_logger()


# -----------------------------------------------------------------------------
# Serialization & Formatting Helpers
# -----------------------------------------------------------------------------
@dataclass
class LogEvent:
    sender: str
    recipient: str
    message_type: str
    payload: Any
    timestamp: str


def to_serializable(val: Any) -> Any:
    """Recursively convert SDK types, objects, or structures into clean JSON-serializable types."""
    if val is None or isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, bytes):
        return val.hex()
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
        return {str(k): to_serializable(v) for k, v in val.items() if v is not None}
    if isinstance(val, (list, tuple, set)):
        return [to_serializable(item) for item in val]
    if hasattr(val, "__dict__"):
        try:
            return {
                str(k): to_serializable(v)
                for k, v in val.__dict__.items()
                if not k.startswith("_") and v is not None
            }
        except Exception:
            pass
    return str(val)


# -----------------------------------------------------------------------------
# Core Logging Functions
# -----------------------------------------------------------------------------
def log_prompt(user_query: str) -> None:
    """Add a line with '=== PROMPT ===' to the log file to mark each prompt."""
    agent_logger.info("=== PROMPT ===")
    log_event(
        sender="user",
        recipient="agent",
        message_type="prompt",
        payload={"query": user_query},
    )


def log_event(sender: str, recipient: str, message_type: str, payload: Any = None) -> None:
    """Log an interaction message passed between AI Agent, LLM, tools, and skills."""
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
    agent_logger.info("%s\n%s", header, body)
