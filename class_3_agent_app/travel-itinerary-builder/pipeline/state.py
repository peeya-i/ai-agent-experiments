"""Global State Schema and utilities for Travel Itinerary Builder."""

from typing import Any, Dict, List
from pydantic import BaseModel, Field


class UserInput(BaseModel):
    """User preferences schema."""
    city_of_origin: str = ""
    destination: str
    budget: float
    days: int
    interests: List[str] = Field(default_factory=list)
    departure_date: str = ""


class FlightResearchItem(BaseModel):
    """Flight option item."""
    flight_name: str
    airline: str = ""
    travel_time: str = ""
    estimated_cost: float
    notes: str = ""


class HotelResearchItem(BaseModel):
    """Hotel option item."""
    hotel_name: str
    tier: str = "mid-range"  # luxury, mid-range, budget, hostel
    price_per_night: float
    safety_rating: str = "Safe"
    location_notes: str = ""


class ActivityResearchItem(BaseModel):
    """Activity option item."""
    activity_name: str
    category: str = "sightseeing"  # landmark, restaurant, tour, nature, culture
    estimated_cost: float = 0.0
    duration_hours: float = 2.0
    description: str = ""


class RawResearch(BaseModel):
    """Aggregated raw research data."""
    flights: List[Dict[str, Any]] = Field(default_factory=list)
    hotels: List[Dict[str, Any]] = Field(default_factory=list)
    activities: List[Dict[str, Any]] = Field(default_factory=list)


class EventItem(BaseModel):
    """Scheduled event."""
    time: str
    title: str
    category: str
    estimated_cost: float = 0.0
    description: str = ""


class DaySchedule(BaseModel):
    """Day-by-day schedule."""
    day: int
    events: List[Dict[str, Any]] = Field(default_factory=list)


class CurrentItinerary(BaseModel):
    """Current generated itinerary."""
    total_estimated_cost: float = 0.0
    schedule: List[Dict[str, Any]] = Field(default_factory=list)


class GlobalTravelState(BaseModel):
    """Centralized Global State schema required by SPECIFICATIONS.md."""
    user_input: Dict[str, Any]
    raw_research: Dict[str, Any]
    current_itinerary: Dict[str, Any]
    critic_feedback: str = ""
    budget_approved: bool = False


def create_initial_state(
    destination: str,
    budget: float,
    days: int,
    interests: List[str],
    city_of_origin: str = "",
    departure_date: str = ""
) -> Dict[str, Any]:
    """Creates the initial centralized dictionary state."""
    return {
        "user_input": {
            "city_of_origin": str(city_of_origin or "").strip(),
            "destination": str(destination).strip(),
            "budget": float(budget),
            "days": int(days),
            "interests": [str(i).strip() for i in interests if str(i).strip()],
            "departure_date": str(departure_date or "").strip()
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


def validate_state(state: Dict[str, Any]) -> bool:
    """Validates that the dictionary conforms to the Global State Schema."""
    required_keys = [
        "user_input",
        "raw_research",
        "current_itinerary",
        "critic_feedback",
        "budget_approved"
    ]
    for key in required_keys:
        if key not in state:
            return False
            
    user_input = state["user_input"]
    if not isinstance(user_input, dict):
        return False
    if "destination" not in user_input or "budget" not in user_input or "days" not in user_input:
        return False
        
    raw_research = state["raw_research"]
    if not isinstance(raw_research, dict):
        return False
    if "flights" not in raw_research or "hotels" not in raw_research or "activities" not in raw_research:
        return False
        
    current_itinerary = state["current_itinerary"]
    if not isinstance(current_itinerary, dict):
        return False
    if "total_estimated_cost" not in current_itinerary or "schedule" not in current_itinerary:
        return False
        
    return True
