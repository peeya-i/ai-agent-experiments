"""Tools for Skill 2: User House Information.

Contains the python code for the tools to answer questions about the user's house:
- get_house_color: Returns the color of the house (always blue)
- get_house_city: Returns the city where the house is located (always San Jose)
- get_private_house_information: Answers questions regarding color and/or city
"""

from __future__ import annotations

from typing import Any

# Import logging functions from the logging module
try:
    from logging import log_event  # type: ignore
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from logging import log_event  # type: ignore

HOUSE_COLOR = "blue"
HOUSE_CITY = "San Jose"


def get_house_color() -> dict[str, str]:
    """Get the color of the user's house. The color is always blue."""
    log_event("agent", "skill_2:house_color", "tool_call", {})
    result = {
        "color": HOUSE_COLOR,
        "answer": f"The color of the house is {HOUSE_COLOR}.",
    }
    log_event("skill_2:house_color", "agent", "tool_response", result)
    return result


def get_house_city() -> dict[str, str]:
    """Get the city where the user's house is located. The city is always San Jose."""
    log_event("agent", "skill_2:house_city", "tool_call", {})
    result = {
        "city": HOUSE_CITY,
        "answer": f"The house is located in {HOUSE_CITY}.",
    }
    log_event("skill_2:house_city", "agent", "tool_response", result)
    return result


def get_private_house_information(question: str) -> dict[str, Any]:
    """Get the color of the house and/or the city where the user's house is located.

    The color of the house is always blue.
    The city where the house is located is always San Jose.
    """
    log_event("agent", "skill_2:house_info", "tool_call", {"question": question})
    q = question.lower()
    has_color = any(w in q for w in ("color", "colour", "paint"))
    has_city = any(w in q for w in ("city", "location", "located", "where", "town"))

    if has_color and has_city:
        result = {
            "house_color": HOUSE_COLOR,
            "house_city": HOUSE_CITY,
            "answer": f"The house is {HOUSE_COLOR} and is located in {HOUSE_CITY}.",
        }
    elif has_color:
        result = {
            "house_color": HOUSE_COLOR,
            "answer": f"The color of the house is {HOUSE_COLOR}.",
        }
    elif has_city:
        result = {
            "house_city": HOUSE_CITY,
            "answer": f"The house is located in {HOUSE_CITY}.",
        }
    else:
        # Default to providing both facts when the user asks a general house question
        result = {
            "house_color": HOUSE_COLOR,
            "house_city": HOUSE_CITY,
            "answer": f"The house is {HOUSE_COLOR} and is located in {HOUSE_CITY}.",
        }

    log_event("skill_2:house_info", "agent", "tool_response", result)
    return result
