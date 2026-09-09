"""Global state definition matching the specifications schema."""
from typing import Dict, Any, List, Optional
import copy

def create_initial_state(
    destination: str,
    budget: float,
    days: int,
    interests: List[str],
    origin: str = "",
    departure_date: Optional[str] = None
) -> Dict[str, Any]:
    """Creates a fresh Global State dictionary conforming to SPECIFICATIONS.md."""
    return {
        "user_input": {
            "origin": origin or "Default Origin",
            "destination": destination,
            "budget": float(budget),
            "days": int(days),
            "departure_date": departure_date or "",
            "interests": [i.strip() for i in interests if i.strip()] if isinstance(interests, list) else [interests]
        },
        "raw_research": {
            "flights": [],
            "hotels": [],
            "activities": []
        },
        "current_itinerary": {
            "total_estimated_cost": 0.0,
            "schedule": []
        },
        "critic_feedback": "",
        "budget_approved": False
    }

def clone_state(state: Dict[str, Any]) -> Dict[str, Any]:
    return copy.deepcopy(state)
