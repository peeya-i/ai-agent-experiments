"""House registry flat-file resolution tool.

Enforces strict case-insensitive containment scanning over the static database lines
to completely block hallucinated data paths.
"""

import csv
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_FILE_PATH = Path(__file__).parent.parent / "data" / "registry.csv"

# Callback hook for audit logging
_registry_audit_logger: Optional[Callable[[str, str, str, str, Dict[str, Any]], None]] = None


def set_registry_audit_logger(callback: Optional[Callable[[str, str, str, str, Dict[str, Any]], None]]) -> None:
    """Set optional callback to record registry access audits.

    Signature: callback(event_type, invoker, target, payload)
    """
    global _registry_audit_logger
    _registry_audit_logger = callback


def _record_audit(event_type: str, invoker: str, target: str, payload: Dict[str, Any]) -> None:
    if _registry_audit_logger:
        try:
            _registry_audit_logger(event_type, invoker, target, payload)
        except Exception as e:
            logger.debug(f"Registry audit callback error: {e}")


def _load_registry() -> List[Dict[str, str]]:
    if not DATA_FILE_PATH.exists():
        logger.error(f"Registry file not found at {DATA_FILE_PATH}")
        return []

    records = []
    with open(DATA_FILE_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({k.strip(): v.strip() for k, v in row.items()})
    return records


def lookup_house_record(name: str) -> Dict[str, Any]:
    """Look up a house record in the registry by resident name using strict case-insensitive containment.

    Args:
        name: Name of the resident or homeowner (e.g. 'Smith', 'Johnson', 'Davis').

    Returns:
        Dictionary containing resident details (name, city, country, house_color) if found,
        or a structured error message indicating the record does not exist.
    """
    _record_audit("TOOL_INVOCATION", "Agent", "house-registry-skill", {"action": "lookup_house_record", "name": name})

    query = name.strip().lower()
    records = _load_registry()

    matched_record = None
    for row in records:
        row_name = row.get("name", "").strip().lower()
        # Strict containment scan
        if query == row_name or query in row_name or row_name in query:
            matched_record = row
            break

    if matched_record:
        result = {
            "status": "found",
            "name": matched_record.get("name"),
            "city": matched_record.get("city"),
            "country": matched_record.get("country"),
            "house_color": matched_record.get("house_color"),
            "source": "registry.csv",
        }
    else:
        result = {
            "status": "not_found",
            "message": f"No record found for resident '{name}' in the verified house registry.",
            "source": "registry.csv",
        }

    _record_audit("TOOL_RESPONSE", "house-registry-skill", "Agent", {"name": name, "result": result})
    return result


def list_registry_records() -> Dict[str, Any]:
    """Retrieve all verified records from the house registry flat-file database."""
    _record_audit("TOOL_INVOCATION", "Agent", "house-registry-skill", {"action": "list_registry_records"})
    records = _load_registry()
    result = {
        "status": "success",
        "total_count": len(records),
        "records": records,
    }
    _record_audit("TOOL_RESPONSE", "house-registry-skill", "Agent", result)
    return result


def search_by_criteria(city: str = "", house_color: str = "", country: str = "") -> Dict[str, Any]:
    """Search the registry database by city, country, or house color.

    Args:
        city: City name to match against.
        house_color: House color to match against.
        country: Country name to match against.
    """
    _record_audit("TOOL_INVOCATION", "Agent", "house-registry-skill", {
        "action": "search_by_criteria",
        "city": city,
        "house_color": house_color,
        "country": country,
    })

    records = _load_registry()
    matches = []

    for row in records:
        if city and city.strip().lower() not in row.get("city", "").strip().lower():
            continue
        if house_color and house_color.strip().lower() not in row.get("house_color", "").strip().lower():
            continue
        if country and country.strip().lower() not in row.get("country", "").strip().lower():
            continue
        matches.append(row)

    result = {
        "status": "success",
        "match_count": len(matches),
        "matches": matches,
    }
    _record_audit("TOOL_RESPONSE", "house-registry-skill", "Agent", result)
    return result
