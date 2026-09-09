"""Tracker service for logging requests to usages.csv and event logs to events.json."""
import csv
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import config

_lock = threading.Lock()

import re

API_KEY_PATTERNS = [
    re.compile(r'AIza[0-9A-Za-z_\-]{20,}'),
    re.compile(r'AQ\.[0-9A-Za-z_\-]{20,}'),
]

def redact_api_key(data: Any, key_to_redact: Optional[str] = None) -> Any:
    """Recursively redacts API keys, tokens, and credentials from strings, dicts, and lists."""
    keys = []
    if config.GEMINI_API_KEY:
        keys.append(config.GEMINI_API_KEY)
    if key_to_redact:
        keys.append(key_to_redact)

    # First pass: collect any explicit secret string values from sensitive dict keys
    def collect_keys(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_lower = str(k).lower()
                if any(term in k_lower for term in ("api_key", "apikey", "secret_key", "access_token", "auth_token")):
                    if isinstance(v, str) and len(v.strip()) >= 4:
                        keys.append(v.strip())
                collect_keys(v)
        elif isinstance(obj, list):
            for item in obj:
                collect_keys(item)

    collect_keys(data)

    def apply_redaction(obj):
        if isinstance(obj, str):
            res = obj
            for k in keys:
                if k and k in res:
                    res = res.replace(k, "[REDACTED_API_KEY]")
            for pat in API_KEY_PATTERNS:
                res = pat.sub("[REDACTED_API_KEY]", res)
            return res
        elif isinstance(obj, dict):
            res = {}
            for k, v in obj.items():
                k_lower = str(k).lower()
                if any(term in k_lower for term in ("api_key", "apikey", "secret_key", "access_token", "auth_token")):
                    res[k] = "[REDACTED_API_KEY]"
                else:
                    res[k] = apply_redaction(v)
            return res
        elif isinstance(obj, list):
            return [apply_redaction(item) for item in obj]
        return obj

    return apply_redaction(data)

def _ensure_files():
    with _lock:
        if not os.path.exists(config.USAGES_CSV):
            with open(config.USAGES_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "run_id",
                    "timestamp",
                    "travel_date",
                    "days",
                    "destination",
                    "origin",
                    "budget",
                    "estimated_cost",
                    "budget_approved",
                    "status",
                    "iterations",
                    "events_count"
                ])
        if not os.path.exists(config.EVENTS_JSON):
            with open(config.EVENTS_JSON, "w", encoding="utf-8") as f:
                pass

        # Migrate multi-line JSON array to single-line event logs if needed
        if os.path.exists(config.EVENTS_JSON) and os.path.getsize(config.EVENTS_JSON) > 0:
            try:
                with open(config.EVENTS_JSON, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content.startswith("["):
                    items = json.loads(content)
                    with open(config.EVENTS_JSON, "w", encoding="utf-8") as f:
                        for ev in items:
                            f.write(json.dumps(ev) + "\n")
            except Exception:
                pass

_ensure_files()

class Tracker:
    @staticmethod
    def redact(data: Any, key: Optional[str] = None) -> Any:
        return redact_api_key(data, key)

    @staticmethod
    def record_event(
        run_id: str,
        event_type: str,
        agent_source: str,
        summary: str,
        payload: Any = None
    ) -> Dict[str, Any]:
        """Appends a new event entry into events.json as a single line with redacted API key."""
        clean_payload = redact_api_key(payload if payload is not None else {})
        clean_summary = redact_api_key(summary) if isinstance(summary, str) else summary

        event_entry = {
            "event_id": f"evt_{uuid.uuid4().hex[:8]}",
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "event_type": event_type,
            "agent_source": agent_source,
            "summary": clean_summary,
            "payload": clean_payload
        }
        with _lock:
            with open(config.EVENTS_JSON, "a", encoding="utf-8") as f:
                f.write(json.dumps(event_entry) + "\n")
        return event_entry

    @staticmethod
    def record_usage(
        run_id: str,
        origin: str,
        destination: str,
        days: int,
        budget: float,
        estimated_cost: float,
        budget_approved: bool,
        status: str,
        iterations: int,
        events_count: int,
        travel_date: Optional[str] = None
    ):
        """Appends or updates a record in usages.csv."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        formatted_travel_date = travel_date.strip() if travel_date and travel_date.strip() else "Flexible"

        fieldnames = [
            "run_id", "timestamp", "travel_date", "days", "destination",
            "origin", "budget", "estimated_cost", "budget_approved", "status",
            "iterations", "events_count"
        ]

        with _lock:
            rows = []
            updated = False
            if os.path.exists(config.USAGES_CSV):
                with open(config.USAGES_CSV, "r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get("run_id") == run_id:
                            row["timestamp"] = timestamp
                            row["travel_date"] = formatted_travel_date
                            row["days"] = str(days)
                            row["destination"] = destination
                            row["origin"] = origin
                            row["budget"] = f"{budget:.2f}"
                            row["estimated_cost"] = f"{estimated_cost:.2f}"
                            row["budget_approved"] = str(budget_approved)
                            row["status"] = status
                            row["iterations"] = str(iterations)
                            row["events_count"] = str(events_count)
                            updated = True
                        else:
                            if "travel_date" not in row:
                                row["travel_date"] = "Flexible"
                        rows.append(row)

            if not updated:
                rows.append({
                    "run_id": run_id,
                    "timestamp": timestamp,
                    "travel_date": formatted_travel_date,
                    "days": str(days),
                    "destination": destination,
                    "origin": origin,
                    "budget": f"{budget:.2f}",
                    "estimated_cost": f"{estimated_cost:.2f}",
                    "budget_approved": str(budget_approved),
                    "status": status,
                    "iterations": str(iterations),
                    "events_count": str(events_count)
                })

            with open(config.USAGES_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

    @staticmethod
    def save_run_itinerary(run_id: str, state: Dict[str, Any]):
        """Saves the complete state/itinerary for a run."""
        file_path = os.path.join(config.RUNS_DIR, f"{run_id}.json")
        with _lock:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

    @staticmethod
    def get_run_itinerary(run_id: str) -> Optional[Dict[str, Any]]:
        file_path = os.path.join(config.RUNS_DIR, f"{run_id}.json")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    @staticmethod
    def get_all_usages() -> List[Dict[str, Any]]:
        with _lock:
            if not os.path.exists(config.USAGES_CSV):
                return []
            with open(config.USAGES_CSV, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return list(reader)[::-1]  # Most recent first

    @staticmethod
    def get_all_events() -> List[Dict[str, Any]]:
        with _lock:
            if not os.path.exists(config.EVENTS_JSON):
                return []
            events = []
            try:
                with open(config.EVENTS_JSON, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                events.append(json.loads(line))
                            except Exception:
                                pass
                if not events:
                    with open(config.EVENTS_JSON, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content.startswith("["):
                            events = json.loads(content)
            except Exception:
                return []
            return events

    @staticmethod
    def get_events_for_run(run_id: str) -> List[Dict[str, Any]]:
        events = Tracker.get_all_events()
        return [e for e in events if e.get("run_id") == run_id]

    @staticmethod
    def get_metrics() -> Dict[str, int]:
        usages = Tracker.get_all_usages()
        total_itineraries = len(usages)
        successful_runs = sum(1 for u in usages if u.get("status") == "success" or u.get("budget_approved") == "True")
        failed_runs = sum(1 for u in usages if u.get("status") == "failed" or (u.get("status") != "success" and u.get("budget_approved") != "True"))
        total_events = len(Tracker.get_all_events())
        return {
            "total_itineraries": total_itineraries,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "total_events": total_events
        }
