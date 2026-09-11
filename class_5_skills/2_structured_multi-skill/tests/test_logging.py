"""Unit tests for logging.py module: redaction, JSON formatting, and query helpers."""

import json
from pathlib import Path
import pytest
import uuid

import logging
from logging import (
    AuditLogger,
    get_conversations,
    get_conversation_events,
    get_event_detail,
    log_event,
    redact_payload,
)


def test_redact_payload_api_keys():
    """Verify Google API key patterns and sensitive dict keys are redacted."""
    sensitive_data = {
        "api_key": "secret_abc_123",
        "nested": {
            "token": "bearer_token_xyz",
            "prompt": "Call with key AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q and execute",
        },
        "items": [
            "Normal string",
            {"key": "private_pass"},
            "Authorization: Bearer secret_bearer_token_456"
        ]
    }

    cleaned = redact_payload(sensitive_data)
    assert cleaned["api_key"] == "[REDACTED_API_KEY]"
    assert cleaned["nested"]["token"] == "[REDACTED_API_KEY]"
    assert "[REDACTED_API_KEY]" in cleaned["nested"]["prompt"]
    assert "AIzaSy" not in cleaned["nested"]["prompt"]
    assert cleaned["items"][1]["key"] == "[REDACTED_API_KEY]"
    assert "[REDACTED_TOKEN]" in cleaned["items"][2]


def test_log_event_and_query(tmp_path):
    """Verify log_event records well-formed JSON and query methods retrieve it."""
    test_log_file = tmp_path / "test_audit.jsonl"
    logger = AuditLogger(log_path=test_log_file)

    c_id = f"test-conv-{uuid.uuid4().hex[:8]}"

    logger.log_event(c_id, "USER_QUERY", "User", "Agent", {"query": "Hello test agent"})
    logger.log_event(c_id, "TOOL_INVOCATION", "Agent", "datetime-weather-skill", {"tool": "get_weather"})
    logger.log_event(c_id, "AGENT_RESPONSE", "Agent", "User", {"response": "Hello back!"})

    # Read back raw file lines
    with open(test_log_file, "r") as f:
        lines = [json.loads(line) for line in f if line.strip()]

    assert len(lines) == 3
    assert lines[0]["event_type"] == "USER_QUERY"
    assert lines[1]["event_type"] == "TOOL_INVOCATION"
    assert lines[2]["event_type"] == "AGENT_RESPONSE"

    # Test conversation summary
    convs = logger.get_conversations()
    assert len(convs) == 1
    assert convs[0]["conversation_id"] == c_id
    assert convs[0]["user_query"] == "Hello test agent"
    assert convs[0]["agent_response"] == "Hello back!"

    # Test conversation events
    events = logger.get_conversation_events(c_id)
    assert len(events) == 3
    assert events[0]["invoker"] == "User"
    assert events[1]["target"] == "datetime-weather-skill"
    assert "short_description" in events[0]
    assert "Hello test agent" in events[0]["short_description"]

    # Test event detail
    ev_id = events[0]["event_id"]
    detail = logger.get_event_detail(ev_id)
    assert detail is not None
    assert detail["payload"]["query"] == "Hello test agent"


def test_agent_invocation_short_description_with_selected_model():
    """Verify AGENT_INVOCATION short description shows selected model instead of hardcoded default."""
    from logging import generate_short_description

    payload = {
        "target_model": "gemini-3.5-flash-lite",
        "requested_model": "gemini-3.5-flash-lite",
        "primary_model": "gemma-4-26b-a4b-it",
        "fallback_model": "gemini-3.5-flash-lite",
        "available_skills": [{"name": "skill-1"}, {"name": "skill-2"}],
    }
    desc = generate_short_description("AGENT_INVOCATION", "User", "Agent", payload)
    assert desc == "Agent initialized with gemini-3.5-flash-lite (2 domain skills ready)"

