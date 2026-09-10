"""Asynchronous JSON audit logging module with API key redaction and stdlib logging proxying.

Adheres to struct_multi-skill.md requirements:
- Logs ALL Agent, LLM, Tool, and External API invocations in logs/ directory in JSON format.
- Contains actual payloads with all fields.
- Redacts API keys in payloads.
- Writes asynchronously to avoid blocking agent execution.
- Integrates seamlessly with standard library logging.
"""

import sys
import os
import importlib.util

# Step 1: Ensure the standard library logging is loaded first to prevent shadowing/circular import
_current_dir = os.path.dirname(os.path.abspath(__file__))
_filtered_path = [p for p in sys.path if os.path.abspath(p) != _current_dir and p not in ("", ".")]

_stdlib_logging = None
for p in _filtered_path:
    candidate = os.path.join(p, "logging", "__init__.py")
    if os.path.exists(candidate):
        _stdlib_dir = os.path.dirname(candidate)
        spec = importlib.util.spec_from_file_location(
            "logging", candidate, submodule_search_locations=[_stdlib_dir]
        )
        _stdlib_logging = importlib.util.module_from_spec(spec)
        sys.modules["logging"] = _stdlib_logging
        spec.loader.exec_module(_stdlib_logging)
        break

if _stdlib_logging is None:
    import logging as _stdlib_logging  # Fallback

# Step 2: Import other standard modules safely (deferred asyncio import to prevent circularity)
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import uuid

# Directory and file paths
LOGS_DIR = Path(_current_dir) / "logs"
AUDIT_LOG_FILE = LOGS_DIR / "agent_audit.jsonl"

# Sensitive patterns and keys to redact
API_KEY_REGEX = re.compile(r"AIza[0-9A-Za-z\-_]{20,}")
SENSITIVE_KEYS = {"api_key", "apikey", "key", "authorization", "secret", "token", "password", "google_api_key"}


def redact_payload(obj: Any) -> Any:
    """Recursively redacts API keys and sensitive tokens from dictionaries, lists, and strings."""
    actual_key = os.environ.get("GOOGLE_API_KEY")
    if isinstance(obj, dict):
        redacted = {}
        for k, v in obj.items():
            if str(k).lower() in SENSITIVE_KEYS:
                redacted[k] = "[REDACTED_API_KEY]"
            else:
                redacted[k] = redact_payload(v)
        return redacted
    elif isinstance(obj, list):
        return [redact_payload(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(redact_payload(item) for item in obj)
    elif isinstance(obj, str):
        sanitized = obj
        if actual_key and len(actual_key) > 5 and actual_key in sanitized:
            sanitized = sanitized.replace(actual_key, "[REDACTED_API_KEY]")
        sanitized = API_KEY_REGEX.sub("[REDACTED_API_KEY]", sanitized)
        sanitized = re.sub(r"Bearer\s+[A-Za-z0-9\-_\.]+", "Bearer [REDACTED_TOKEN]", sanitized)
        return sanitized
    elif hasattr(obj, "to_json_dict"):
        try:
            return redact_payload(obj.to_json_dict())
        except Exception:
            return str(obj)
    elif hasattr(obj, "model_dump"):
        try:
            return redact_payload(obj.model_dump())
        except Exception:
            return str(obj)
    return obj


def generate_short_description(event_type: str, invoker: str, target: str, payload: Any) -> str:
    """Generate a concise human-readable description for an audit event."""
    if not isinstance(payload, dict):
        text = str(payload)
        return text[:75] + "..." if len(text) > 75 else text

    if event_type == "USER_QUERY":
        q = str(payload.get("query", ""))
        return f"User query: '{q[:60]}...'" if len(q) > 60 else f"User query: '{q}'"

    if event_type == "AGENT_INVOCATION":
        m = payload.get("primary_model", "LLM")
        tools = payload.get("available_tools", [])
        return f"Agent initialized with {m} ({len(tools)} skills/tools bound)" if tools else f"Agent initialized with {m}"

    if event_type == "LLM_REQUEST":
        turn = payload.get("turn", 1)
        model = payload.get("model", "LLM")
        num_contents = len(payload.get("contents", []))
        return f"Turn {turn}: Inference request to {model} ({num_contents} content parts)"

    if event_type == "LLM_RESPONSE":
        turn = payload.get("turn") or payload.get("_metadata", {}).get("turn", 1)
        # Extract function call names from candidate parts or top-level
        call_names = []
        candidates = payload.get("candidates") or []
        if isinstance(candidates, list) and len(candidates) > 0:
            content = candidates[0].get("content") or {}
            parts = content.get("parts") or []
            for p in parts:
                if isinstance(p, dict) and p.get("function_call"):
                    call_names.append(p["function_call"].get("name", "function"))
        if not call_names and payload.get("function_calls"):
            fc = payload.get("function_calls", [])
            call_names = [c.get("name", "") for c in fc if isinstance(c, dict)]
        if call_names:
            return f"Turn {turn}: LLM requested function call(s): {', '.join(call_names)}"

        # Extract generated text from candidates or preview
        text = ""
        if isinstance(candidates, list) and len(candidates) > 0:
            content = candidates[0].get("content") or {}
            parts = content.get("parts") or []
            for p in parts:
                if isinstance(p, dict) and p.get("text"):
                    text = p["text"]
                    break
        if not text:
            text = payload.get("text_preview", "")
        if text:
            clean_text = text.replace("\n", " ")
            return f"Turn {turn}: LLM text '{clean_text[:45]}...'" if len(clean_text) > 45 else f"Turn {turn}: LLM text '{clean_text}'"
        return f"Turn {turn}: LLM response received"

    if event_type == "TOOL_INVOCATION":
        tool = payload.get("tool") or payload.get("name") or payload.get("action", "tool")
        args = payload.get("arguments") or payload.get("args", {})
        arg_str = ", ".join(f"{k}={v}" for k, v in args.items()) if isinstance(args, dict) else str(args)
        return f"Invoke {tool}({arg_str})"

    if event_type == "TOOL_RESPONSE":
        tool = payload.get("tool") or payload.get("name", "tool")
        res = payload.get("response") or payload.get("result", {})
        if isinstance(res, dict) and "result" in res:
            res = res["result"]
        if isinstance(res, dict):
            status = res.get("status", "completed")
            name = res.get("name", "")
            city = res.get("city", "")
            cond = res.get("condition", "")
            temp = res.get("temperature_celsius")
            if temp is not None:
                return f"{tool}: {cond}, {temp}°C in {city}"
            if name and city:
                return f"{tool}: Resident '{name}' in {city}"
            return f"{tool}: status='{status}'"
        return f"{tool} returned result"

    if event_type == "EXTERNAL_API_REQUEST":
        city = payload.get("city") or (payload.get("params", {}).get("q") if isinstance(payload.get("params"), dict) else "")
        return f"HTTP request to {target} ({city})" if city else f"HTTP request to {target}"

    if event_type == "EXTERNAL_API_RESPONSE":
        code = payload.get("status_code", 200)
        return f"HTTP {code} response received from {invoker}"

    if event_type == "AGENT_RESPONSE":
        resp = str(payload.get("response", ""))
        return f"Agent answer: '{resp[:60]}...'" if len(resp) > 60 else f"Agent answer: '{resp}'"

    return f"{invoker} -> {target} ({event_type})"


class AuditLogger:
    """Asynchronous JSON audit logger using background async thread execution."""

    def __init__(self, log_path: Path = AUDIT_LOG_FILE):
        self.log_path = log_path
        self._pending_tasks = set()
        self._ensure_log_dir()

    def _ensure_log_dir(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    def _append_line_sync(self, line: str) -> None:
        with open(self.log_path, mode="a", encoding="utf-8") as f:
            f.write(line)
            f.flush()

    async def _async_write_line(self, line: str) -> None:
        import asyncio
        await asyncio.to_thread(self._append_line_sync, line)

    async def flush(self) -> None:
        """Wait until all pending async write tasks have finished writing to disk."""
        import asyncio
        if self._pending_tasks:
            tasks = list(self._pending_tasks)
            await asyncio.gather(*tasks, return_exceptions=True)
            self._pending_tasks.clear()

    def log_event(
        self,
        conversation_id: str,
        event_type: str,
        invoker: str,
        target: str,
        payload: Any,
        metadata: Optional[Dict[str, Any]] = None,
        short_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record an audit event.

        Can be called from sync or async contexts. Redacts sensitive payloads and
        writes asynchronously via background worker to avoid blocking agent execution.
        """
        self._ensure_log_dir()
        event_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        clean_payload = redact_payload(payload)
        desc = short_description or generate_short_description(event_type, invoker, target, clean_payload)

        event_data = {
            "event_id": event_id,
            "conversation_id": conversation_id,
            "timestamp": timestamp,
            "event_type": event_type,
            "invoker": invoker,
            "target": target,
            "short_description": desc,
            "payload": clean_payload,
            "metadata": metadata or {},
        }
        line = json.dumps(event_data, default=str) + "\n"

        try:
            import asyncio
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._async_write_line(line))
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)
        except (RuntimeError, ImportError):
            self._append_line_sync(line)

        return event_data

    def get_all_events(self) -> List[Dict[str, Any]]:
        """Reads all events from the audit log file."""
        self._ensure_log_dir()
        events = []
        if not self.log_path.exists():
            return events

        with open(self.log_path, mode="r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except Exception:
                        pass
        return events

    def _partition_events_by_conversation_turn(self, events: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Partitions raw events into isolated conversation-turn buckets.

        If a conversation_id contains only 1 user query, it retains the base conversation_id.
        If a conversation_id contains multiple user queries (e.g. consecutive questions asked in
        the same session), each query exchange is cleanly partitioned into its own distinct turn:
        f"{c_id}-turn-{turn_number}" so that Table 1 and Table 2 strictly isolate each inquiry
        and its respective LLM/tool event traces.
        """
        by_base: Dict[str, List[Dict[str, Any]]] = {}
        for ev in events:
            c_id = ev.get("conversation_id")
            if not c_id:
                continue
            by_base.setdefault(c_id, []).append(ev)

        result: Dict[str, List[Dict[str, Any]]] = {}
        for c_id, ev_list in by_base.items():
            query_count = sum(1 for ev in ev_list if ev.get("event_type") == "USER_QUERY")
            if query_count <= 1:
                result[c_id] = ev_list
            else:
                current_turn = 1
                turn_events: List[Dict[str, Any]] = []
                turn_has_response = False
                for ev in ev_list:
                    if turn_has_response and ev.get("event_type") in ("USER_QUERY", "AGENT_INVOCATION"):
                        turn_key = f"{c_id}-turn-{current_turn}"
                        result[turn_key] = turn_events
                        current_turn += 1
                        turn_events = []
                        turn_has_response = False
                    turn_events.append(ev)
                    if ev.get("event_type") == "AGENT_RESPONSE":
                        turn_has_response = True
                if turn_events:
                    turn_key = f"{c_id}-turn-{current_turn}"
                    result[turn_key] = turn_events

        return result

    def get_conversations(self) -> List[Dict[str, Any]]:
        """Returns conversation summaries for the Log Review Table 1.

        Columns:
        - Conversation ID
        - Timestamp
        - User Query
        - Agent Response
        """
        events = self.get_all_events()
        partitioned = self._partition_events_by_conversation_turn(events)
        conversations: List[Dict[str, Any]] = []

        for conv_key, ev_list in partitioned.items():
            first_ev = ev_list[0] if ev_list else {}
            conv_entry = {
                "conversation_id": conv_key,
                "timestamp": first_ev.get("timestamp", ""),
                "user_query": "",
                "agent_response": "",
                "event_count": len(ev_list),
            }

            for ev in ev_list:
                ev_type = ev.get("event_type")
                payload = ev.get("payload", {})
                if ev_type == "USER_QUERY" and not conv_entry["user_query"]:
                    if isinstance(payload, dict):
                        conv_entry["user_query"] = payload.get("query", str(payload))
                    else:
                        conv_entry["user_query"] = str(payload)
                elif ev_type == "AGENT_RESPONSE" and not conv_entry["agent_response"]:
                    if isinstance(payload, dict):
                        conv_entry["agent_response"] = payload.get("response", str(payload))
                    else:
                        conv_entry["agent_response"] = str(payload)

            conversations.append(conv_entry)

        conversations.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return conversations

    def get_conversation_events(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Returns the events for a specific conversation for Log Review Table 2.

        Columns:
        - Timestamp
        - Event Type
        - Invoker
        - Target
        - Short Description
        """
        events = self.get_all_events()
        partitioned = self._partition_events_by_conversation_turn(events)

        if conversation_id in partitioned:
            target_events = partitioned[conversation_id]
        else:
            # Fallback to direct conversation_id match for standard query
            target_events = [ev for ev in events if ev.get("conversation_id") == conversation_id]

        filtered = [
            {
                "event_id": ev.get("event_id"),
                "timestamp": ev.get("timestamp"),
                "event_type": ev.get("event_type"),
                "invoker": ev.get("invoker"),
                "target": ev.get("target"),
                "short_description": ev.get("short_description")
                or generate_short_description(
                    ev.get("event_type", ""),
                    ev.get("invoker", ""),
                    ev.get("target", ""),
                    ev.get("payload", {}),
                ),
                "payload": ev.get("payload"),
                "metadata": ev.get("metadata"),
            }
            for ev in target_events
        ]
        filtered.sort(key=lambda x: x.get("timestamp", ""))
        return filtered

    def get_event_detail(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Returns the complete event payload for modal inspection."""
        events = self.get_all_events()
        for ev in events:
            if ev.get("event_id") == event_id:
                return ev
        return None


# Global singleton instance
audit_logger = AuditLogger()


def log_event(
    conversation_id: str,
    event_type: str,
    invoker: str,
    target: str,
    payload: Any,
    metadata: Optional[Dict[str, Any]] = None,
    short_description: Optional[str] = None,
) -> Dict[str, Any]:
    return audit_logger.log_event(conversation_id, event_type, invoker, target, payload, metadata, short_description)


def get_conversations() -> List[Dict[str, Any]]:
    return audit_logger.get_conversations()


def get_conversation_events(conversation_id: str) -> List[Dict[str, Any]]:
    return audit_logger.get_conversation_events(conversation_id)


def get_event_detail(event_id: str) -> Optional[Dict[str, Any]]:
    return audit_logger.get_event_detail(event_id)


async def flush_logs() -> None:
    await audit_logger.flush()


# Expose our custom functions and classes on sys.modules['logging'] as well
_current_module = sys.modules.get("logging")
if _current_module:
    _current_module.AuditLogger = AuditLogger
    _current_module.audit_logger = audit_logger
    _current_module.log_event = log_event
    _current_module.flush_logs = flush_logs
    _current_module.get_conversations = get_conversations
    _current_module.get_conversation_events = get_conversation_events
    _current_module.get_event_detail = get_event_detail
    _current_module.redact_payload = redact_payload

# Also copy all stdlib symbols to globals for anyone doing "from logging import getLogger"
for _attr in dir(_stdlib_logging):
    if not _attr.startswith("__") and _attr not in globals():
        globals()[_attr] = getattr(_stdlib_logging, _attr)
