"""Core Orchestrator utilizing the official google-genai SDK and modular domain skills.

Implements requirements:
- Google GenAI SDK integration with tools parameter in GenerateContentConfig.
- Asynchronous validation match loop over response.function_calls.
- Logs ALL Agent, LLM, Tool, and External API invocations via logging.py.
- Imports API key and models from .env (with fallback model support).
- Anti-hallucination containment enforcement for house registry.
"""

import asyncio
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
import uuid

import dotenv
dotenv.load_dotenv()

# Add skill script paths to sys.path so modules can be imported directly
BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR / "skills" / "datetime-weather-skill" / "scripts"))
sys.path.append(str(BASE_DIR / "skills" / "house-registry-skill" / "scripts"))
sys.path.append(str(BASE_DIR / "skills" / "plant-care-skill" / "scripts"))

# Import skill functions
from env_tools import get_weather, get_local_time, set_external_api_logger
from registry_tools import lookup_house_record, list_registry_records, set_registry_audit_logger
from plant_tools import get_plant_care_instructions, get_plant_care_template, list_common_houseplants

# Import logging module with fallback for pre-loaded stdlib logging
try:
    from logging import log_event
except ImportError:
    import importlib.util
    spec = importlib.util.spec_from_file_location("local_logging", BASE_DIR / "logging.py")
    _lmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_lmod)
    log_event = _lmod.log_event

import logging as std_logging
logger = std_logging.getLogger("multi_skill_agent")

# Import google-genai
from google import genai
from google.genai import types

# Structured definitions for all available domain skills
SKILL_DEFINITIONS = {
    "datetime-weather-skill": {
        "name": "datetime-weather-skill",
        "description": "Real-time weather forecasts, current temperature, and local time resolution for global cities.",
        "tools": [get_weather, get_local_time],
        "tool_names": ["get_weather", "get_local_time"],
        "info": (
            "### Skill: datetime-weather-skill\n"
            "- Description: Real-time public weather analytics and local datetime resolution for global locations without requiring proprietary API keys.\n"
            "- Available Tools:\n"
            "  * 'get_weather(city)': Fetch real-time weather analytics (temperature, condition, humidity, wind speed) for a specified city.\n"
            "  * 'get_local_time(city)': Get current local date, time, and timezone information for a specified city.\n"
            "- Standard Operating Procedure (SOP):\n"
            "  1. Extract the target city from the user query or previous lookup.\n"
            "  2. Query 'get_weather' and/or 'get_local_time' for that city.\n"
            "  3. Synthesize structured, accurate weather and time analytics."
        ),
    },
    "house-registry-skill": {
        "name": "house-registry-skill",
        "description": "Verified flat-file registry containing property records (resident name, city, country, house color).",
        "tools": [lookup_house_record, list_registry_records],
        "tool_names": ["lookup_house_record", "list_registry_records"],
        "info": (
            "### Skill: house-registry-skill\n"
            "- Description: Strict registry resolution for property assets, resident locations, and house colors using flat-file database records.\n"
            "- Available Tools:\n"
            "  * 'lookup_house_record(name)': Look up house registry records (resident name, city, country, house color) strictly from the flat-file database.\n"
            "  * 'list_registry_records()': Retrieve all verified records from the house registry flat-file database.\n"
            "- Standard Operating Procedure (SOP):\n"
            "  1. Strict Non-Hallucination Policy: You MUST NOT guess, extrapolate, or invent property or resident details. Only information verified through containment scanning over registry records may be reported.\n"
            "  2. Case-Insensitive Matching: Normalize resident names and query strings to match database records.\n"
            "  3. Report exact stored attributes: Resident Name, City, Country, and House Color.\n"
            "  4. If a requested resident cannot be found, explicitly state that no record exists in the verified database."
        ),
    },
    "plant-care-skill": {
        "name": "plant-care-skill",
        "description": "Botanical reference and comprehensive plant care instructions formatted according to standardized horticultural templates.",
        "tools": [get_plant_care_instructions, get_plant_care_template, list_common_houseplants],
        "tool_names": ["get_plant_care_instructions", "get_plant_care_template", "list_common_houseplants"],
        "info": (
            "### Skill: plant-care-skill\n"
            "- Description: Botanical reference and comprehensive plant care instructions formatted according to standardized horticultural templates.\n"
            "- Available Tools:\n"
            "  * 'get_plant_care_instructions(plant_name)': Retrieve comprehensive plant care instructions and botanical guide for a specific plant.\n"
            "  * 'get_plant_care_template()': Retrieve the standardized markdown template for plant care formatting.\n"
            "  * 'list_common_houseplants()': List popular common houseplants with botanical classifications and pet safety.\n"
            "- Standard Operating Procedure (SOP):\n"
            "  1. When asked about plants, plant care, watering, soil, repotting, or propagation, retrieve data using 'get_plant_care_instructions'.\n"
            "  2. Adhere strictly to the comprehensive markdown care template including Plant Information, Soil and Potting, Light Requirements, Watering & Moisture, Temperature and Humidity, Routine Maintenance & Grooming, Propagation, Common Pests & Troubleshooting, and ASPCA Pet Safety & Toxicity."
        ),
    },
}

SKILL_ROUTING_INSTRUCTION = """You are an intelligent multi-skill agent coordinator.
Analyze the user's query and decide which domain skill(s) should be activated to answer it.

Available Skills:
1. 'datetime-weather-skill': Real-time weather forecasts, current temperature, and local time resolution for global cities.
2. 'house-registry-skill': Verified flat-file registry containing property records (resident name, city, country, house color).
3. 'plant-care-skill': Botanical reference and comprehensive plant care instructions formatted according to standardized horticultural templates.

Routing Rules:
- If the query requires a skill, name the skill (e.g., 'house-registry-skill', 'datetime-weather-skill', 'plant-care-skill').
- If the query requires multiple skills (e.g., "What is the weather where Smith lives?"), list all applicable skills.
- If the query does not require any domain skill (e.g., general conversation, greetings, simple math, or general knowledge like "What is the capital of France?"), respond with 'NONE'.
- Format your response strictly as:
SKILLS: [comma-separated skill names or NONE]
REASONING: [one brief sentence explaining why]
"""


def _parse_selected_skills(response_text: str, query: str) -> tuple[List[str], str]:
    """Parses model response to determine which skill(s) should be activated."""
    raw = (response_text or "").strip()
    reasoning = ""
    skills_line = ""

    for line in raw.splitlines():
        line_clean = line.strip()
        if line_clean.upper().startswith("SKILLS:"):
            skills_line = line_clean[len("SKILLS:"):].strip()
        elif line_clean.upper().startswith("REASONING:"):
            reasoning = line_clean[len("REASONING:"):].strip()

    if not reasoning:
        reasoning = raw

    text_to_scan = (skills_line or raw).lower()

    if "none" in text_to_scan and not any(s in text_to_scan for s in ["datetime", "weather", "house", "registry", "plant"]):
        return [], reasoning

    selected = []
    if any(k in text_to_scan for k in ["datetime-weather-skill", "weather", "forecast", "temperature", "local time", "datetime", "timezone"]):
        selected.append("datetime-weather-skill")

    if any(k in text_to_scan for k in ["house-registry-skill", "house", "registry", "resident", "house color", "lives in"]):
        selected.append("house-registry-skill")

    if any(k in text_to_scan for k in ["plant-care-skill", "plant", "plants", "botany", "gardening", "watering", "monstera", "snake plant", "pothos"]):
        selected.append("plant-care-skill")

    seen = set()
    deduped = []
    for s in selected:
        if s not in seen:
            seen.add(s)
            deduped.append(s)

    # Fallback if no skills were extracted from response text but query clearly targets a skill
    if not deduped:
        q_lower = query.lower()
        if any(k in q_lower for k in ["weather", "temperature", "forecast", "time in", "what time"]):
            deduped.append("datetime-weather-skill")
        if any(k in q_lower for k in ["house", "resident", "lives", "color of", "registry", "who lives"]):
            deduped.append("house-registry-skill")
        if any(k in q_lower for k in ["plant", "plants", "botany", "watering", "soil", "repot", "care for"]):
            deduped.append("plant-care-skill")

    return deduped, reasoning


def _build_turn2_system_instruction(selected_skills: List[str]) -> str:
    """Builds Turn 2 system instructions incorporating relevant skill information and SOP."""
    if not selected_skills:
        return (
            "You are a helpful and knowledgeable AI assistant.\n"
            "Answer the user's query directly, accurately, and politely using general knowledge."
        )

    sections = [
        "You are an autonomous AI agent with specialized domain skills.\n"
        "In Turn 1, skill routing activated the following relevant domain skill(s) for this query:\n"
    ]
    for skill_name in selected_skills:
        skill_def = SKILL_DEFINITIONS.get(skill_name)
        if skill_def:
            sections.append(skill_def["info"])

    if len(selected_skills) > 1:
        sections.append(
            "### Multi-Skill Coordination SOP:\n"
            "When a query involves multiple domains (such as finding the weather where a resident lives):\n"
            "1. First invoke 'lookup_house_record' to determine the resident's verified city.\n"
            "2. Once the city is resolved from the tool response, invoke 'get_weather' and/or 'get_local_time' for that city.\n"
            "3. Synthesize all verified details into a comprehensive, accurate final response."
        )

    sections.append(
        "CRITICAL OPERATIONAL RULES:\n"
        "- Use the provided tools to retrieve real verified data. Do NOT guess or hallucinate any domain records.\n"
        "- If a record or item is not found, state clearly that it was not found in the verified data.\n"
        "- Provide clear, friendly, and complete answers based strictly on the tool responses."
    )

    return "\n\n".join(sections)


def _serialize_payload(obj: Any) -> Any:
    """Recursively serializes GenAI SDK objects (Part, Content, GenerateContentResponse, FunctionCall) to dicts."""
    if hasattr(obj, "model_dump"):
        try:
            return _serialize_payload(obj.model_dump())
        except Exception:
            pass
    if hasattr(obj, "to_json_dict"):
        try:
            return _serialize_payload(obj.to_json_dict())
        except Exception:
            pass
    if isinstance(obj, dict):
        return {k: _serialize_payload(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_payload(i) for i in obj]
    if isinstance(obj, tuple):
        return tuple(_serialize_payload(i) for i in obj)
    return obj


MODEL_ALIASES = {
    "gemma 4 26b": "gemma-4-26b-a4b-it",
    "gemma-4-26b": "gemma-4-26b-a4b-it",
    "gemma 4 31b": "gemma-4-31b-it",
    "gemma-4-31b": "gemma-4-31b-it",
    "gemini 3.5 flash lite": "gemini-3.5-flash-lite",
    "gemini-3.5-flash-lite": "gemini-3.5-flash-lite",
    "gemini 3.8 flash": "gemini-3.8-flash",
    "gemini-3.8-flash": "gemini-3.8-flash",
}


def resolve_model_name(model_name: Optional[str], default_model: str) -> str:
    """Resolves UI / user friendly model names and aliases to canonical model IDs."""
    if not model_name or not str(model_name).strip():
        return default_model
    clean = str(model_name).strip()
    return MODEL_ALIASES.get(clean.lower(), clean)


class MultiSkillAgent:
    """Orchestrator managing multi-skill execution with Google GenAI SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        primary_model: Optional[str] = None,
        fallback_model: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set.")

        self.primary_model = primary_model or os.environ.get("MODEL", "gemma-4-26b-a4b-it")
        self.fallback_model = fallback_model or os.environ.get("FALLBACK_MODEL", "gemini-3.5-flash-lite")

        # Initialize GenAI client
        self.client = genai.Client(api_key=self.api_key)

        # Declarations of native python tools to bind into GenerateContentConfig
        self.tools = [
            get_weather,
            get_local_time,
            lookup_house_record,
            list_registry_records,
            get_plant_care_instructions,
            get_plant_care_template,
            list_common_houseplants,
        ]

        # Mapping for execution dispatch & target labeling in audit logs
        self.tool_dispatch = {
            "get_weather": (get_weather, "datetime-weather-skill"),
            "get_local_time": (get_local_time, "datetime-weather-skill"),
            "lookup_house_record": (lookup_house_record, "house-registry-skill"),
            "list_registry_records": (list_registry_records, "house-registry-skill"),
            "get_plant_care_instructions": (get_plant_care_instructions, "plant-care-skill"),
            "get_plant_care_template": (get_plant_care_template, "plant-care-skill"),
            "list_common_houseplants": (list_common_houseplants, "plant-care-skill"),
        }

    def _call_model(self, model: str, contents: Any, config: types.GenerateContentConfig):
        """Invoke GenAI model with automatic fallback handling."""
        try:
            return self.client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            ), model
        except Exception as e:
            logger.warning(f"Primary model '{model}' encountered an error: {e}. Attempting fallback to '{self.fallback_model}'.")
            if model != self.fallback_model:
                try:
                    return self.client.models.generate_content(
                        model=self.fallback_model,
                        contents=contents,
                        config=config,
                    ), self.fallback_model
                except Exception as fb_err:
                    logger.error(f"Fallback model '{self.fallback_model}' also failed: {fb_err}")
                    raise fb_err
            raise e

    async def run(
        self,
        user_query: str,
        conversation_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute agent workflow with Turn 1 skill routing and Turn 2 execution."""
        c_id = conversation_id or f"conv-{uuid.uuid4().hex[:12]}"

        # Hook external API audit logs to include current conversation_id
        def _ext_logger(ev_type: str, invoker: str, target: str, payload: Dict[str, Any]):
            log_event(c_id, ev_type, invoker, target, payload)

        set_external_api_logger(_ext_logger)
        set_registry_audit_logger(None)

        # Resolve model to use (from request override, alias resolution, or default primary model)
        target_model = resolve_model_name(model, self.primary_model)
        active_model = target_model

        # 1. Log incoming user query and agent workflow invocation
        log_event(c_id, "USER_QUERY", "User", "Agent", {"query": user_query})
        log_event(c_id, "AGENT_INVOCATION", "User", "Agent", {
            "model": target_model,
            "target_model": target_model,
            "requested_model": model,
            "primary_model": self.primary_model,
            "fallback_model": self.fallback_model,
            "query": user_query,
            "available_skills": [
                {"name": k, "description": v["description"], "tools": v["tool_names"]}
                for k, v in SKILL_DEFINITIONS.items()
            ],
        })

        # =========================================================================
        # TURN 1: Ask the model which skill to use
        # =========================================================================
        turn1_contents = [user_query]
        turn1_config = types.GenerateContentConfig(
            system_instruction=SKILL_ROUTING_INSTRUCTION,
            temperature=0.1,
        )

        log_event(c_id, "LLM_REQUEST", "Agent", "LLM", {
            "model": active_model,
            "turn": 1,
            "phase": "skill_selection",
            "query": user_query,
            "contents": [_serialize_payload(c) for c in turn1_contents],
            "system_instruction": SKILL_ROUTING_INSTRUCTION,
            "temperature": 0.1,
            "available_skills": [
                {"name": k, "description": v["description"]}
                for k, v in SKILL_DEFINITIONS.items()
            ],
        })

        routing_response, used_model = await asyncio.to_thread(
            self._call_model, active_model, turn1_contents, turn1_config
        )
        active_model = used_model

        routing_text = routing_response.text or ""
        selected_skills, reasoning = _parse_selected_skills(routing_text, user_query)

        routing_dump = _serialize_payload(routing_response)
        if isinstance(routing_dump, dict):
            routing_dump["_metadata"] = {
                "model": active_model,
                "turn": 1,
                "phase": "skill_selection",
                "selected_skills": selected_skills,
                "reasoning": reasoning,
            }
        log_event(c_id, "LLM_RESPONSE", "LLM", "Agent", routing_dump)

        # Resolve tools for Turn 2 based on selected skills
        turn2_tools = []
        for s_name in selected_skills:
            s_def = SKILL_DEFINITIONS.get(s_name)
            if s_def:
                for fn in s_def["tools"]:
                    if fn not in turn2_tools:
                        turn2_tools.append(fn)

        log_event(c_id, "SKILL_SELECTION", "Agent", "Agent", {
            "selected_skills": selected_skills,
            "reasoning": reasoning,
            "raw_response": routing_text,
            "tools_bound": [fn.__name__ for fn in turn2_tools],
            "tools_bound_count": len(turn2_tools),
        })

        # =========================================================================
        # TURN 2+: Add information from relevant skills and execute interaction
        # =========================================================================
        turn2_system_instruction = _build_turn2_system_instruction(selected_skills)

        if turn2_tools:
            turn2_config = types.GenerateContentConfig(
                system_instruction=turn2_system_instruction,
                tools=turn2_tools,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                temperature=0.1,
            )
        else:
            turn2_config = types.GenerateContentConfig(
                system_instruction=turn2_system_instruction,
                temperature=0.1,
            )

        contents: List[Any] = [user_query]
        max_turns = 10
        turn_count = 1
        final_text = ""

        try:
            while turn_count < max_turns:
                turn_count += 1

                # Log full actual LLM Request payload for Turn 2+
                log_event(c_id, "LLM_REQUEST", "Agent", "LLM", {
                    "model": active_model,
                    "turn": turn_count,
                    "phase": "execution",
                    "contents": [_serialize_payload(c) for c in contents],
                    "system_instruction": turn2_system_instruction,
                    "temperature": 0.1,
                    "tools": [
                        {"name": fn.__name__, "description": fn.__doc__}
                        for fn in turn2_tools
                    ],
                })

                # Call Model in async executor
                response, used_model = await asyncio.to_thread(
                    self._call_model, active_model, contents, turn2_config
                )
                active_model = used_model

                # Log full actual LLM Response payload
                full_response_dump = _serialize_payload(response)
                if isinstance(full_response_dump, dict):
                    full_response_dump["_metadata"] = {
                        "model": active_model,
                        "turn": turn_count,
                        "phase": "execution",
                    }
                log_event(c_id, "LLM_RESPONSE", "LLM", "Agent", full_response_dump)

                function_calls = getattr(response, "function_calls", None)

                if not function_calls:
                    final_text = response.text or "I have processed your request."
                    break

                # Implements validation match over response.function_calls loop
                if response.candidates and response.candidates[0].content:
                    contents.append(response.candidates[0].content)

                tool_response_parts = []
                for call in function_calls:
                    fn_name = call.name
                    fn_args = call.args or {}

                    if fn_name in self.tool_dispatch:
                        fn_obj, skill_target = self.tool_dispatch[fn_name]

                        # Log full actual tool invocation payload
                        call_payload = _serialize_payload(call)
                        if isinstance(call_payload, dict):
                            call_payload["tool"] = fn_name
                        log_event(c_id, "TOOL_INVOCATION", "Agent", skill_target, call_payload)

                        # Execute tool in async thread
                        try:
                            tool_result = await asyncio.to_thread(fn_obj, **fn_args)
                        except Exception as tool_err:
                            tool_result = {"status": "error", "error": str(tool_err)}

                        # Log full actual tool response payload
                        log_event(c_id, "TOOL_RESPONSE", skill_target, "Agent", {
                            "tool": fn_name,
                            "call_id": getattr(call, "id", None),
                            "arguments": fn_args,
                            "result": tool_result,
                        })

                        # Route generated parameters safely back into final response synthesis stage
                        tool_response_parts.append(types.Part.from_function_response(
                            name=fn_name,
                            response={"result": tool_result}
                        ))
                    else:
                        logger.error(f"Unrecognized function call name: {fn_name}")
                        tool_response_parts.append(types.Part.from_function_response(
                            name=fn_name,
                            response={"result": f"Unknown tool: {fn_name}"}
                        ))

                if tool_response_parts:
                    contents.append(types.Content(role="user", parts=tool_response_parts))

            if not final_text:
                final_text = "Completed multi-skill processing."

        except Exception as err:
            logger.error(f"Error during agent execution: {err}", exc_info=True)
            final_text = f"An error occurred while processing your request: {err}"

        # Log final Agent Response to User with full metadata
        log_event(c_id, "AGENT_RESPONSE", "Agent", "User", {
            "response": final_text,
            "conversation_id": c_id,
            "model_used": active_model,
            "requested_model": model,
            "selected_skills": selected_skills,
            "total_turns": turn_count,
        })
        try:
            from logging import flush_logs
            await flush_logs()
        except Exception:
            pass

        return {
            "conversation_id": c_id,
            "response": final_text,
            "model_used": active_model,
            "requested_model": model,
            "selected_skills": selected_skills,
        }


# Global agent instance
_agent_instance: Optional[MultiSkillAgent] = None


def get_agent() -> MultiSkillAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = MultiSkillAgent()
    return _agent_instance
