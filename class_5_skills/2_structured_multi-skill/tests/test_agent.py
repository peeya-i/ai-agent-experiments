"""Unit tests for agent.py orchestrator."""

import pytest
import asyncio
from pathlib import Path
import sys

BASE_DIR = Path(__file__).parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agent import MultiSkillAgent, get_agent


@pytest.fixture
def agent():
    return get_agent()


def test_agent_initialization(agent):
    """Verify MultiSkillAgent initializes with GenAI client and required tools across all 3 skills."""
    assert agent.client is not None
    assert len(agent.tools) == 7
    tool_names = [f.__name__ for f in agent.tools]
    assert "get_weather" in tool_names
    assert "get_local_time" in tool_names
    assert "lookup_house_record" in tool_names
    assert "list_registry_records" in tool_names
    assert "get_plant_care_instructions" in tool_names
    assert "get_plant_care_template" in tool_names
    assert "list_common_houseplants" in tool_names


def test_agent_tool_dispatch(agent):
    """Verify tool dispatch mappings match skill domains."""
    assert "get_weather" in agent.tool_dispatch
    assert agent.tool_dispatch["get_weather"][1] == "datetime-weather-skill"
    assert "lookup_house_record" in agent.tool_dispatch
    assert agent.tool_dispatch["lookup_house_record"][1] == "house-registry-skill"
    assert "get_plant_care_instructions" in agent.tool_dispatch
    assert agent.tool_dispatch["get_plant_care_instructions"][1] == "plant-care-skill"


def test_agent_run_house_lookup(agent):
    """Verify agent executes house lookup correctly via GenAI tool calling loop."""
    result = asyncio.run(agent.run("Where does Davis live and what is the color of the house?"))
    assert "conversation_id" in result
    assert "response" in result
    resp = result["response"].lower()
    assert "san jose" in resp
    assert "green" in resp


def test_agent_run_weather_lookup(agent):
    """Verify agent executes weather lookup via GenAI tool calling loop."""
    result = asyncio.run(agent.run("What is the current weather in Paris?"))
    assert "conversation_id" in result
    assert "response" in result
    resp = result["response"]
    assert len(resp) > 10


def test_agent_run_plant_care_lookup(agent):
    """Verify agent executes plant care guide retrieval via GenAI tool calling loop."""
    result = asyncio.run(agent.run("How do I care for a Snake Plant at home?"))
    assert "conversation_id" in result
    assert "response" in result
    assert "selected_skills" in result
    assert "plant-care-skill" in result["selected_skills"]
    resp = result["response"].lower()
    assert "snake plant" in resp or "water" in resp or "light" in resp


def test_parse_selected_skills_logic():
    """Verify skill selection parser handles structured, unstructured, multi-skill, and NONE outputs."""
    from agent import _parse_selected_skills

    # 1. Single skill structured
    skills, reasoning = _parse_selected_skills("SKILLS: house-registry-skill\nREASONING: Resident query.", "Where is Kim?")
    assert skills == ["house-registry-skill"]

    # 2. Multi-skill structured
    skills, reasoning = _parse_selected_skills("SKILLS: house-registry-skill, datetime-weather-skill\nREASONING: Need house and weather.", "Weather where Smith lives?")
    assert "house-registry-skill" in skills
    assert "datetime-weather-skill" in skills

    # 3. NONE structured
    skills, reasoning = _parse_selected_skills("SKILLS: NONE\nREASONING: General knowledge question.", "What is the capital of France?")
    assert skills == []

    # 4. Freeform text
    skills, reasoning = _parse_selected_skills("I recommend activating plant-care-skill to give horticultural guidelines.", "How to propagate monstera?")
    assert skills == ["plant-care-skill"]


def test_skill_selection_logged_in_audit_trace(agent):
    """Verify Turn 1 skill selection generates a SKILL_SELECTION audit log event."""
    from logging import get_conversation_events

    result = asyncio.run(agent.run("Where is Kim?"))
    conv_id = result["conversation_id"]
    assert "house-registry-skill" in result["selected_skills"]

    events = get_conversation_events(conv_id)
    event_types = [e["event_type"] for e in events]
    assert "SKILL_SELECTION" in event_types

    selection_ev = [e for e in events if e["event_type"] == "SKILL_SELECTION"][0]
    assert "house-registry-skill" in selection_ev["payload"]["selected_skills"]
    assert selection_ev["payload"]["tools_bound_count"] == 2


def test_resolve_model_name():
    """Verify resolve_model_name handles dropdown presets, aliases, and custom inputs."""
    from agent import resolve_model_name

    assert resolve_model_name(None, "default-model") == "default-model"
    assert resolve_model_name("", "default-model") == "default-model"
    assert resolve_model_name("Gemma 4 26B", "default-model") == "gemma-4-26b-a4b-it"
    assert resolve_model_name("Gemma 4 31B", "default-model") == "gemma-4-31b-it"
    assert resolve_model_name("Gemini 3.5 flash lite", "default-model") == "gemini-3.5-flash-lite"
    assert resolve_model_name("Gemini 3.8 flash", "default-model") == "gemini-3.8-flash"
    assert resolve_model_name("custom-private-model-v1", "default-model") == "custom-private-model-v1"


def test_agent_run_with_custom_model_parameter(agent):
    """Verify agent.run accepts model parameter and logs requested_model."""
    from logging import get_conversation_events

    result = asyncio.run(agent.run("Where is Kim?", model="gemini-3.5-flash-lite"))
    assert result["requested_model"] == "gemini-3.5-flash-lite"
    assert "gemini-3.5-flash-lite" in result["model_used"]

    events = get_conversation_events(result["conversation_id"])
    agent_inv_ev = [e for e in events if e["event_type"] == "AGENT_INVOCATION"][0]
    assert agent_inv_ev["payload"]["requested_model"] == "gemini-3.5-flash-lite"


