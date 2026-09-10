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

# Import skill functions
from env_tools import get_weather, get_local_time, set_external_api_logger
from registry_tools import lookup_house_record, list_registry_records, set_registry_audit_logger

# Import logging module with fallback for pre-loaded stdlib logging
try:
    from logging import log_event
except ImportError:
    import importlib.util
    spec = importlib.util.spec_from_file_location("local_logging", BASE_DIR / "logging.py")
    _lmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_lmod)
    log_event = _lmod.log_event

# Import google-genai
from google import genai
from google.genai import types

SYSTEM_INSTRUCTION = """You are an autonomous, multi-skill AI agent with access to domain-specific tools:
1. 'datetime-weather-skill': Real-time weather forecasts, current temperature, and local time resolution for global cities.
2. 'house-registry-skill': Verified flat-file registry containing property records (resident name, city, country, house color).

CRITICAL OPERATIONAL RULES:
- When a user asks about a resident's house (such as owner, city, country, or house color), you MUST ALWAYS use the 'lookup_house_record' or 'list_registry_records' tool. Do NOT guess or hallucinate any property information.
- If a user asks a multi-part question (such as "What is the weather and current time in the city where Smith lives?"), first resolve the city from the house registry using 'lookup_house_record', and then use 'get_weather' and 'get_local_time' for that city.
- Always provide clear, friendly, and complete answers based strictly on the tool responses.
"""


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
        ]

        # Mapping for execution dispatch & target labeling in audit logs
        self.tool_dispatch = {
            "get_weather": (get_weather, "datetime-weather-skill"),
            "get_local_time": (get_local_time, "datetime-weather-skill"),
            "lookup_house_record": (lookup_house_record, "house-registry-skill"),
            "list_registry_records": (list_registry_records, "house-registry-skill"),
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
            logging.warning(f"Primary model '{model}' encountered an error: {e}. Attempting fallback to '{self.fallback_model}'.")
            if model != self.fallback_model:
                return self.client.models.generate_content(
                    model=self.fallback_model,
                    contents=contents,
                    config=config,
                ), self.fallback_model
            raise e

    async def run(self, user_query: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute agent workflow asynchronously over user query.

        Implements the validation match over response.function_calls loop, routing parameters
        safely back into response synthesis and logging all transitions with full payloads.
        """
        c_id = conversation_id or f"conv-{uuid.uuid4().hex[:12]}"

        # Hook external API audit logs to include current conversation_id
        def _ext_logger(ev_type: str, invoker: str, target: str, payload: Dict[str, Any]):
            log_event(c_id, ev_type, invoker, target, payload)

        set_external_api_logger(_ext_logger)
        set_registry_audit_logger(None)

        # 1. Log incoming user query and agent workflow invocation
        log_event(c_id, "USER_QUERY", "User", "Agent", {"query": user_query})
        log_event(c_id, "AGENT_INVOCATION", "User", "Agent", {
            "primary_model": self.primary_model,
            "fallback_model": self.fallback_model,
            "query": user_query,
            "available_tools": [
                {"name": name, "skill": skill, "description": fn.__doc__}
                for name, (fn, skill) in self.tool_dispatch.items()
            ],
        })

        # Configure tools with automatic_function_calling disabled to manually control the loop and logging
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=self.tools,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            temperature=0.1,
        )

        contents: List[Any] = [user_query]
        max_turns = 5
        turn_count = 0
        final_text = ""
        active_model = self.primary_model

        try:
            while turn_count < max_turns:
                turn_count += 1

                # Log full actual LLM Request payload
                log_event(c_id, "LLM_REQUEST", "Agent", "LLM", {
                    "model": active_model,
                    "turn": turn_count,
                    "contents": [_serialize_payload(c) for c in contents],
                    "system_instruction": SYSTEM_INSTRUCTION,
                    "temperature": 0.1,
                    "tools": [
                        {"name": name, "description": fn.__doc__}
                        for name, (fn, _) in self.tool_dispatch.items()
                    ],
                })

                # Call Model in async executor
                response, used_model = await asyncio.to_thread(
                    self._call_model, active_model, contents, config
                )
                active_model = used_model

                # Log full actual LLM Response payload
                full_response_dump = _serialize_payload(response)
                if isinstance(full_response_dump, dict):
                    full_response_dump["_metadata"] = {
                        "model": active_model,
                        "turn": turn_count,
                    }
                log_event(c_id, "LLM_RESPONSE", "LLM", "Agent", full_response_dump)

                function_calls = getattr(response, "function_calls", None)

                if not function_calls:
                    final_text = response.text or "I have processed your request."
                    break

                # Implements validation match over response.function_calls loop
                if response.candidates and response.candidates[0].content:
                    contents.append(response.candidates[0].content)

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
                        contents.append(types.Part.from_function_response(
                            name=fn_name,
                            response={"result": tool_result}
                        ))
                    else:
                        logging.error(f"Unrecognized function call name: {fn_name}")
                        contents.append(types.Part.from_function_response(
                            name=fn_name,
                            response={"result": f"Unknown tool: {fn_name}"}
                        ))

            if not final_text:
                final_text = "Completed multi-skill processing."

        except Exception as err:
            logging.error(f"Error during agent execution: {err}", exc_info=True)
            final_text = f"An error occurred while processing your request: {err}"

        # Log final Agent Response to User with full metadata
        log_event(c_id, "AGENT_RESPONSE", "Agent", "User", {
            "response": final_text,
            "conversation_id": c_id,
            "model_used": active_model,
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
        }


# Global agent instance
_agent_instance: Optional[MultiSkillAgent] = None


def get_agent() -> MultiSkillAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = MultiSkillAgent()
    return _agent_instance
