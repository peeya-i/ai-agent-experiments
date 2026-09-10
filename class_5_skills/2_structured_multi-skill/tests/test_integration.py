"""Integration tests for web interface endpoints and end-to-end multi-skill flow."""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys

BASE_DIR = Path(__file__).parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_index_page_serves_html(client):
    """Verify GET / returns 200 and serves HTML with 2 pages and tables."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "Page 1: Chat with Agent" in html
    assert "Page 2: Log Review" in html
    assert "table-conversations" in html
    assert "table-events" in html
    assert "Short Description" in html
    assert "json-modal" in html


def test_chat_endpoint_and_audit_log_trace(client):
    """Verify /api/chat runs multi-skill workflow and populates conversation and event logs."""
    # Send a query
    chat_resp = client.post(
        "/api/chat",
        json={"message": "What is the house color of Tanaka and where does he live?"}
    )
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert "conversation_id" in data
    assert "response" in data
    conv_id = data["conversation_id"]

    # Verify conversation is in /api/conversations (Table 1)
    convs_resp = client.get("/api/conversations")
    assert convs_resp.status_code == 200
    convs = convs_resp.json().get("conversations", [])
    matching = [c for c in convs if c["conversation_id"] == conv_id]
    assert len(matching) == 1
    assert "Tanaka" in matching[0]["user_query"]
    assert len(matching[0]["agent_response"]) > 0

    # Verify conversation events in /api/conversations/{conv_id}/events (Table 2)
    events_resp = client.get(f"/api/conversations/{conv_id}/events")
    assert events_resp.status_code == 200
    events = events_resp.json().get("events", [])
    assert len(events) >= 4

    event_types = [e["event_type"] for e in events]
    assert "USER_QUERY" in event_types
    assert "AGENT_INVOCATION" in event_types
    assert "TOOL_INVOCATION" in event_types
    assert "TOOL_RESPONSE" in event_types
    assert "AGENT_RESPONSE" in event_types

    # Verify Short Description column field is populated on all events
    assert all("short_description" in e and len(e["short_description"]) > 0 for e in events)

    # Verify individual event detail modal endpoint
    first_ev_id = events[0]["event_id"]
    detail_resp = client.get(f"/api/events/{first_ev_id}")
    assert detail_resp.status_code == 200
    ev_detail = detail_resp.json().get("event", {})
    assert ev_detail["event_id"] == first_ev_id
    assert "payload" in ev_detail


def test_api_key_redaction_in_logs(client):
    """Verify that simulated API keys in queries or responses are redacted in the logs."""
    fake_key_query = "Test query with key AIzaSyD3xFakeKeyForTestingRedaction12345"
    chat_resp = client.post("/api/chat", json={"message": fake_key_query})
    assert chat_resp.status_code == 200
    conv_id = chat_resp.json()["conversation_id"]

    events_resp = client.get(f"/api/conversations/{conv_id}/events")
    events = events_resp.json().get("events", [])
    user_query_ev = [e for e in events if e["event_type"] == "USER_QUERY"][0]

    # Ensure fake key was redacted
    query_str = str(user_query_ev["payload"])
    assert "AIzaSyD3xFakeKey" not in query_str
    assert "[REDACTED_API_KEY]" in query_str
