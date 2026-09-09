import csv
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins import BasePlugin
from google.adk.tools import BaseTool, ToolContext

logger = logging.getLogger(__name__)

# Artifacts paths
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "artifacts"
DEFAULT_EVENTS_FILE = ARTIFACTS_DIR / "events.json"
DEFAULT_USAGES_CSV = ARTIFACTS_DIR / "usages.csv"

CSV_COLUMNS = [
    "timestamp",
    "event_type",
    "user_input",
    "prompt",
    "agent",
    "model",
    "request_contents",
    "config",
    "response",
    "debug_log"
]


def append_usage_to_csv(
    data: Dict[str, Any],
    file_path: Optional[Path] = None
) -> None:
    """Appends a usage record to artifacts/usages.csv with required columns."""
    target_path = file_path or DEFAULT_USAGES_CSV
    target_path = Path(target_path).resolve()

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = target_path.exists() and target_path.stat().st_size > 0

        row = {
            "timestamp": str(data.get("timestamp") or datetime.now(timezone.utc).isoformat()),
            "event_type": str(data.get("event_type", "")),
            "user_input": json.dumps(data.get("user_input", "")) if isinstance(data.get("user_input"), (dict, list)) else str(data.get("user_input", "")),
            "prompt": str(data.get("prompt", "")),
            "agent": str(data.get("agent", "")),
            "model": str(data.get("model", "")),
            "request_contents": json.dumps(data.get("request_contents", "")) if isinstance(data.get("request_contents"), (dict, list)) else str(data.get("request_contents", "")),
            "config": json.dumps(data.get("config", "")) if isinstance(data.get("config"), (dict, list)) else str(data.get("config", "")),
            "response": json.dumps(data.get("response", "")) if isinstance(data.get("response"), (dict, list)) else str(data.get("response", "")),
            "debug_log": str(data.get("debug_log", ""))
        }

        with open(target_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    except Exception as e:
        logger.error("Failed to write usage row to %s: %s", target_path, e)


def serialize_for_json(obj: Any) -> Any:
    """Recursively serializes objects to JSON-compatible data structures."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple, set)):
        return [serialize_for_json(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): serialize_for_json(v) for k, v in obj.items()}
    if hasattr(obj, "model_dump"):
        try:
            return serialize_for_json(obj.model_dump(mode="json"))
        except Exception:
            pass
    if hasattr(obj, "to_dict"):
        try:
            return serialize_for_json(obj.to_dict())
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        try:
            return serialize_for_json(obj.__dict__)
        except Exception:
            pass
    return str(obj)


def append_event_to_json(
    event_entry: Dict[str, Any],
    file_path: Optional[Path] = None
) -> None:
    """Appends a structured event entry to the events.json file in single-line JSON format."""
    target_path = file_path or DEFAULT_EVENTS_FILE
    target_path = Path(target_path).resolve()

    clean_entry = serialize_for_json(event_entry)
    line = json.dumps(clean_entry, ensure_ascii=False)

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        logger.error("Failed to write event to %s: %s", target_path, e)


def read_events_from_json(file_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Reads events from events.json, supporting single-line JSON (JSON Lines) format."""
    target_path = file_path or DEFAULT_EVENTS_FILE
    target_path = Path(target_path).resolve()
    if not target_path.exists():
        return []

    events_list: List[Dict[str, Any]] = []
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            if content.startswith("[") and content.endswith("]"):
                data = json.loads(content)
                return data if isinstance(data, list) else [data]
            for line in content.splitlines():
                line = line.strip()
                if line:
                    events_list.append(json.loads(line))
    except Exception as e:
        logger.warning("Could not read events from %s: %s", target_path, e)
    return events_list


def summarize_event_for_display(ev: Dict[str, Any]) -> Dict[str, Any]:
    """Generates a human-friendly summary of an event for UI rendering."""
    event_type = ev.get("event_type", "unknown")
    agent = ev.get("agent") or "System"
    summary = ""
    details: Dict[str, Any] = {}

    if event_type == "pipeline_start":
        u_in = ev.get("user_input", {})
        dest = u_in.get("destination", "Unknown")
        budget = u_in.get("budget", 0)
        days = u_in.get("days", 0)
        origin = u_in.get("city_of_origin") or u_in.get("origin")
        origin_str = f" from {origin}" if origin else ""
        summary = f"Pipeline initialized for {dest}{origin_str} ({days} days, budget ${budget})"
        details = {"user_input": u_in, "prompt": ev.get("prompt")}

    elif event_type == "model_request":
        model = ev.get("model", "gemini")
        summary = f"Prompt request dispatched to model [{model}]"
        req_c = ev.get("request_contents")
        details = {"request_contents": req_c, "config": ev.get("config")}

    elif event_type == "model_response":
        model_ver = ev.get("model_version") or ev.get("model") or "gemini"
        fr = ev.get("finish_reason", "STOP")
        summary = f"Model response received ({model_ver}) [Finish: {fr}]"
        details = {
            "response_content": ev.get("response_content") or ev.get("response"),
            "usage_metadata": ev.get("usage_metadata")
        }

    elif event_type in ("tool_call", "tool_invocation"):
        tool_name = ev.get("tool_name", "tool")
        is_skill = ev.get("is_skill_tool", False)
        prefix = "Skill" if is_skill else "Tool"
        summary = f"{prefix} [{tool_name}] called with arguments"
        details = {"tool_name": tool_name, "tool_arguments": ev.get("tool_arguments")}

    elif event_type in ("tool_response", "skill_response"):
        tool_name = ev.get("tool_name", "tool")
        is_skill = ev.get("is_skill_tool", False)
        prefix = "Skill" if is_skill else "Tool"
        res_snippet = str(ev.get("tool_result", ""))[:120]
        summary = f"{prefix} [{tool_name}] response returned: {res_snippet}"
        details = {
            "tool_name": tool_name,
            "tool_result": ev.get("tool_result"),
            "state_snapshot": ev.get("state_snapshot")
        }

    elif event_type == "tool_execution":
        tool_name = ev.get("tool", "tool")
        summary = f"Executed [{tool_name}]: {ev.get('result', '')}"
        details = ev

    elif event_type == "pipeline_complete":
        st = ev.get("final_state", {})
        cost = st.get("current_itinerary", {}).get("total_estimated_cost", 0.0)
        approved = st.get("budget_approved", False)
        status_txt = "Approved" if approved else "Over Budget"
        summary = f"Pipeline finalized. Cost: ${cost:.2f} ({status_txt})"
        details = {"final_state": st}

    elif event_type == "pipeline_fallback":
        err = ev.get("error", "Unknown error")
        summary = f"Fallback recovery triggered: {str(err)[:100]}"
        details = {"error": err, "fallback_state": ev.get("fallback_state")}

    else:
        summary = f"Event [{event_type}] processed"
        details = ev

    return {
        "timestamp": ev.get("timestamp"),
        "event_type": event_type,
        "agent": agent,
        "summary": summary,
        "details": details,
        "raw_event": ev
    }


def get_all_itineraries_with_events(file_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Reads events from events.json and groups them into structured itinerary runs."""
    events = read_events_from_json(file_path)
    if not events:
        return []

    itineraries: List[Dict[str, Any]] = []
    current_itin: Optional[Dict[str, Any]] = None

    for ev in events:
        etype = ev.get("event_type")

        # Explicit itinerary_id tag if present, else segment by pipeline_start
        if etype == "pipeline_start":
            if current_itin:
                itineraries.append(current_itin)

            u_in = ev.get("user_input", {})
            current_itin = {
                "id": ev.get("itinerary_id") or f"itin_{len(itineraries) + 1}",
                "start_time": ev.get("timestamp"),
                "end_time": None,
                "destination": u_in.get("destination", "Unknown Destination"),
                "origin": u_in.get("city_of_origin") or u_in.get("origin", ""),
                "departure_date": u_in.get("departure_date", ""),
                "budget": u_in.get("budget"),
                "days": u_in.get("days"),
                "interests": u_in.get("interests", []),
                "total_estimated_cost": None,
                "budget_approved": None,
                "status": "In Progress",
                "events": [],
                "logs": []
            }
            current_itin["events"].append(summarize_event_for_display(ev))
            dest = current_itin["destination"]
            days = current_itin["days"]
            current_itin["logs"].append(f"Started pipeline for {dest} ({days} days)")

        elif current_itin is not None:
            processed_event = summarize_event_for_display(ev)
            current_itin["events"].append(processed_event)

            # Extract logs
            if etype in ("tool_call", "tool_invocation"):
                t_name = ev.get("tool_name", "tool")
                agent_name = ev.get("agent", "Agent")
                current_itin["logs"].append(f"Tool Invoked: [{t_name}] by [{agent_name}]")
            elif etype in ("tool_response", "skill_response"):
                t_name = ev.get("tool_name", "tool")
                current_itin["logs"].append(f"Tool Completed: [{t_name}]")
            elif etype == "model_request":
                current_itin["logs"].append(f"Agent [{ev.get('agent', 'System')}] querying LLM...")
            elif etype == "model_response":
                current_itin["logs"].append(f"Agent [{ev.get('agent', 'System')}] received model response")

            if etype in ("pipeline_complete", "pipeline_fallback"):
                current_itin["end_time"] = ev.get("timestamp")
                current_itin["status"] = "Completed" if etype == "pipeline_complete" else "Fallback"
                state = ev.get("final_state") or ev.get("fallback_state") or {}
                if state:
                    itin_block = state.get("current_itinerary", {})
                    current_itin["total_estimated_cost"] = itin_block.get("total_estimated_cost")
                    current_itin["budget_approved"] = state.get("budget_approved")
                    if not current_itin["origin"]:
                        current_itin["origin"] = state.get("user_input", {}).get("city_of_origin", "")
                    if state.get("logs"):
                        for l in state["logs"]:
                            if l not in current_itin["logs"]:
                                current_itin["logs"].append(l)

    if current_itin:
        itineraries.append(current_itin)

    # Post-process itineraries: ensure unique IDs and calculate counts
    for idx, itin in enumerate(itineraries):
        itin["event_count"] = len(itin["events"])
        # Format display ID
        itin["display_id"] = f"ITIN-{idx+1:03d}"

    # Return reverse-chronological (newest first)
    return list(reversed(itineraries))


def get_itinerary_by_id(
    itinerary_id: str,
    file_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """Returns a specific itinerary with full events and logs by ID."""
    itineraries = get_all_itineraries_with_events(file_path)
    for itin in itineraries:
        if itin.get("id") == itinerary_id or itin.get("display_id") == itinerary_id:
            return itin
    return None



class JsonEventLoggerPlugin(BasePlugin):
    """ADK Plugin to capture model messages, model responses, and tool calls into events.json."""

    def __init__(
        self,
        name: str = "json_event_logger",
        output_file: Optional[Path] = None
    ):
        super().__init__(name=name)
        self.output_file = output_file or DEFAULT_EVENTS_FILE
        self.csv_file = ARTIFACTS_DIR / "usages.csv"

    async def before_model_callback(
        self,
        *,
        callback_context: Any,
        llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        """Records outgoing messages and configuration sent to the model."""
        agent_name = getattr(callback_context, "agent_name", "unknown_agent")

        # Extract contents / prompt messages
        contents = getattr(llm_request, "contents", None)
        model_name = getattr(llm_request, "model", None)
        config = getattr(llm_request, "config", None)

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "model_request",
            "agent": agent_name,
            "model": model_name,
            "request_contents": serialize_for_json(contents),
            "config": serialize_for_json(config),
        }
        append_event_to_json(entry, self.output_file)
        append_usage_to_csv({
            "timestamp": entry["timestamp"],
            "event_type": "model_request",
            "agent": agent_name,
            "model": model_name,
            "request_contents": entry["request_contents"],
            "config": entry["config"],
            "debug_log": f"Model request from agent {agent_name}"
        }, self.csv_file)
        return None

    async def after_model_callback(
        self,
        *,
        callback_context: Any,
        llm_response: LlmResponse
    ) -> Optional[LlmResponse]:
        """Records incoming responses and tool/function calls received from the model."""
        agent_name = getattr(callback_context, "agent_name", "unknown_agent")

        content = getattr(llm_response, "content", None)
        model_version = getattr(llm_response, "model_version", None)
        usage_metadata = getattr(llm_response, "usage_metadata", None)
        finish_reason = getattr(llm_response, "finish_reason", None)

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "model_response",
            "agent": agent_name,
            "model_version": model_version,
            "response_content": serialize_for_json(content),
            "finish_reason": str(finish_reason) if finish_reason else None,
            "usage_metadata": serialize_for_json(usage_metadata),
        }
        append_event_to_json(entry, self.output_file)
        append_usage_to_csv({
            "timestamp": entry["timestamp"],
            "event_type": "model_response",
            "agent": agent_name,
            "model": model_version,
            "response": entry["response_content"],
            "debug_log": f"Model response received for agent {agent_name} (finish_reason={finish_reason})"
        }, self.csv_file)
        return None

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: Dict[str, Any],
        tool_context: ToolContext
    ) -> Optional[Dict[str, Any]]:
        """Records tool and skill invocations before execution."""
        agent_name = getattr(tool_context, "agent_name", "unknown_agent")
        tool_name = getattr(tool, "name", getattr(tool, "__name__", str(tool)))
        is_skill = "skill" in tool_name.lower() or hasattr(tool, "skills")
        event_type = "skill_invocation" if is_skill else "tool_invocation"

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "agent": agent_name,
            "tool_name": tool_name,
            "is_skill_tool": is_skill,
            "tool_arguments": serialize_for_json(tool_args),
        }
        append_event_to_json(entry, self.output_file)
        append_usage_to_csv({
            "timestamp": entry["timestamp"],
            "event_type": event_type,
            "agent": agent_name,
            "request_contents": entry["tool_arguments"],
            "debug_log": f"{'Skill' if is_skill else 'Tool'} {tool_name} invoked by {agent_name}"
        }, self.csv_file)
        return None

    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: Dict[str, Any],
        tool_context: ToolContext,
        result: Any
    ) -> Optional[Dict[str, Any]]:
        """Records tool and skill outputs and responses after execution."""
        agent_name = getattr(tool_context, "agent_name", "unknown_agent")
        tool_name = getattr(tool, "name", getattr(tool, "__name__", str(tool)))
        is_skill = "skill" in tool_name.lower() or hasattr(tool, "skills")
        event_type = "skill_response" if is_skill else "tool_response"

        state_dict = {}
        if hasattr(tool_context, "state"):
            if hasattr(tool_context.state, "to_dict"):
                try:
                    state_dict = tool_context.state.to_dict()
                except Exception:
                    state_dict = getattr(tool_context.state, "_value", {})
            elif hasattr(tool_context.state, "_value"):
                state_dict = getattr(tool_context.state, "_value", {})

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "agent": agent_name,
            "tool_name": tool_name,
            "is_skill_tool": is_skill,
            "tool_arguments": serialize_for_json(tool_args),
            "tool_result": serialize_for_json(result),
            "state_snapshot": serialize_for_json(state_dict)
        }
        append_event_to_json(entry, self.output_file)
        append_usage_to_csv({
            "timestamp": entry["timestamp"],
            "event_type": event_type,
            "agent": agent_name,
            "response": entry["tool_result"],
            "debug_log": f"{'Skill' if is_skill else 'Tool'} {tool_name} completed for agent {agent_name}"
        }, self.csv_file)
        return None
