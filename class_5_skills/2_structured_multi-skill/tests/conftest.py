"""Pytest configuration ensuring local modules and multi-skill logging are registered."""

import importlib.util
import os
from pathlib import Path
import sys

BASE_DIR = Path(__file__).parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure local logging.py attaches its symbols to sys.modules['logging']
local_logging_path = BASE_DIR / "logging.py"
spec = importlib.util.spec_from_file_location("multi_skill_logging", local_logging_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

import logging
for attr in [
    "AuditLogger",
    "audit_logger",
    "log_event",
    "flush_logs",
    "get_conversations",
    "get_conversation_events",
    "get_event_detail",
    "redact_payload",
]:
    if hasattr(mod, attr):
        setattr(logging, attr, getattr(mod, attr))
