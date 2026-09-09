"""Logging module for Multi-Skill AI Agent.

Provides human-readable structured logging to multi-skill_agent.log, masks
API keys for security, marks each prompt with "=== PROMPT ===", and safely
proxies standard library logging symbols so third-party packages (e.g. google.adk)
can import standard logging seamlessly.
"""

from __future__ import annotations

import datetime
import importlib.util
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# -----------------------------------------------------------------------------
# Standard Library Logging Proxy Setup
# -----------------------------------------------------------------------------
# Locate and load the Python standard library logging module to prevent shadowing
# issues when other libraries (such as google.adk or google.genai) perform `import logging`.
_current_dir = Path(__file__).resolve().parent
_stdlib_paths = [p for p in sys.path if p and Path(p).resolve() != _current_dir]
_spec = None
for _p in _stdlib_paths:
    _candidate = Path(_p) / "logging" / "__init__.py"
    if _candidate.exists():
        _spec = importlib.util.spec_from_file_location("_stdlib_logging", str(_candidate))
        break

if _spec and _spec.loader:
    _stdlib_logging = importlib.util.module_from_spec(_spec)
    sys.modules["logging"] = _stdlib_logging
    _spec.loader.exec_module(_stdlib_logging)
    # Expose standard library logging names in this module's globals
    globals().update(
        {k: getattr(_stdlib_logging, k) for k in dir(_stdlib_logging) if not k.startswith("__")}
    )
else:
    # Fallback to normal import if standard library path resolution is atypical
    import logging as _stdlib_logging  # type: ignore

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
class ApiKeyMaskingFilter(_stdlib_logging.Filter):
    """Filter that intercepts and masks API keys anywhere they appear in log records."""

    def filter(self, record: _stdlib_logging.LogRecord) -> bool:
        message = record.getMessage()
        for key in (GOOGLE_API_KEY, OPENWEATHER_API_KEY):
            if key and len(key) > 5:
                message = message.replace(key, "[REDACTED_API_KEY]")
        record.msg = message
        record.args = ()
        return True


# -----------------------------------------------------------------------------
# Logger Initialization
# -----------------------------------------------------------------------------
def setup_agent_logger(log_file: Path | str = LOG_FILE) -> _stdlib_logging.Logger:
    """Initialize and configure the multi-skill agent logger."""
    logger = _stdlib_logging.getLogger("multi_skill_agent")
    logger.setLevel(_stdlib_logging.INFO)
    logger.handlers.clear()

    formatter = _stdlib_logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    masking_filter = ApiKeyMaskingFilter()

    handler = _stdlib_logging.FileHandler(str(log_file), encoding="utf-8")
    handler.setFormatter(formatter)
    handler.addFilter(masking_filter)
    logger.addHandler(handler)

    return logger


_agent_logger = setup_agent_logger()


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


# -----------------------------------------------------------------------------
# Core Logging Functions
# -----------------------------------------------------------------------------
def log_prompt(user_query: str) -> None:
    """Add a line with '=== PROMPT ===' to the log file to mark each prompt."""
    _agent_logger.info("=== PROMPT ===")
    log_event(
        sender="user",
        recipient="agent",
        message_type="prompt",
        payload={"query": user_query},
    )


def log_event(sender: str, recipient: str, message_type: str, payload: Any) -> None:
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
    _agent_logger.info("%s\n%s", header, body)


# Attach custom methods to standard library logging module for maximum compatibility
setattr(_stdlib_logging, "log_prompt", log_prompt)
setattr(_stdlib_logging, "log_event", log_event)
setattr(_stdlib_logging, "setup_agent_logger", setup_agent_logger)
setattr(_stdlib_logging, "ApiKeyMaskingFilter", ApiKeyMaskingFilter)
