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
    resp = result["response"].lower()
    assert "snake plant" in resp or "water" in resp or "light" in resp
