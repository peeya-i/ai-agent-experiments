import os
import sys
import logging
from pathlib import Path
from typing import Optional, List, Dict

from dotenv import load_dotenv

# Ensure workspace root and parent paths are in sys.path
CURRENT_DIR = Path(__file__).resolve().parent
SYSTEMS_DIR = CURRENT_DIR.parent
WORKSPACE_ROOT = SYSTEMS_DIR.parent

for p in [str(WORKSPACE_ROOT), str(SYSTEMS_DIR), str(CURRENT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from adk_utils.callback_logging import (
    setup_logging,
    log_query_to_model,
    log_model_response,
)
from adk_utils.plugins import Graceful429Plugin

from google.adk import Agent
from google.adk.apps.app import App
from google.adk.models import Gemini
from google.adk.tools.tool_context import ToolContext
from google.genai import types

# Load environment variables (.env in agent directory or workspace root)
load_dotenv(CURRENT_DIR / ".env")
load_dotenv(WORKSPACE_ROOT / ".env")

# Initialize local console logging (replaces google.cloud.logging)
setup_logging()

RETRY_OPTIONS = types.HttpRetryOptions(initial_delay=1, max_delay=3, attempts=30)

# Tools
def save_attractions_to_state(
    tool_context: ToolContext,
    attractions: List[str]
) -> dict[str, str]:
    """Saves the list of attractions to state["attractions"].

    Args:
        attractions [str]: a list of strings to add to the list of attractions

    Returns:
        None
    """
    # Load existing attractions from state. If none exist, start an empty list
    existing_attractions = tool_context.state.get("attractions", [])

    # Update the 'attractions' key with a combo of old and new lists.
    # When the tool is run, ADK will create an event and make
    # corresponding updates in the session's state.
    tool_context.state["attractions"] = existing_attractions + attractions

    # A best practice for tools is to return a status message in a return dict
    return {"status": "success"}

# Agents
attractions_planner = Agent(
    name="attractions_planner",
    model=Gemini(model=os.getenv("MODEL"), retry_options=RETRY_OPTIONS),
    description="Build a list of attractions to visit in a country.",
    instruction="""
        - Provide the user options for attractions to visit within their selected country.
        - When they reply, use your tool to save their selected attraction
        and then provide more possible attractions.
        - If they ask to view the list, provide a bulleted list of
        { attractions? } and then suggest some more.
        """,
    before_model_callback=log_query_to_model,
    after_model_callback=log_model_response,
    # Paste the tools parameter below this line
    tools=[save_attractions_to_state]
    )

travel_brainstormer = Agent(
    name="travel_brainstormer",
    model=Gemini(model=os.getenv("MODEL"), retry_options=RETRY_OPTIONS),
    description="Help a user decide what country to visit.",
    instruction="""
        Provide a few suggestions of popular countries for travelers.
        
        Help a user identify their primary goals of travel:
        adventure, leisure, learning, shopping, or viewing art

        Identify countries that would make great destinations
        based on their priorities.
        """,
    before_model_callback=log_query_to_model,
    after_model_callback=log_model_response,
)

root_agent = Agent(
    name="steering",
    model=Gemini(model=os.getenv("MODEL"), retry_options=RETRY_OPTIONS),
    description="Start a user on a travel adventure.",
    instruction="""
        Ask the user if they know where they'd like to travel
        or if they need some help deciding.
        If they need help deciding, send them to
        'travel_brainstormer'.
        If they know what country they'd like to visit,
        send them to the 'attractions_planner'.
        """,
    generate_content_config=types.GenerateContentConfig(
        temperature=0,
    ),
    sub_agents=[travel_brainstormer, attractions_planner]
)

graceful_plugin = Graceful429Plugin(
    name="graceful_429_plugin",
    fallback_text={
        "default": "**[Simulated Response via 429 Graceful Fallback]**\n\nThe API is out of quota. Please retry."
    }
)
graceful_plugin.apply_429_interceptor(root_agent)

app = App(
    name="parent_and_subagents",
    root_agent=root_agent,
    plugins=[graceful_plugin]
)
