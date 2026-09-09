"""Parallel Agent framework executing FlightResearcher, HotelResearcher, and ActivityPlanner concurrently."""
import concurrent.futures
import json
import logging
from typing import Dict, Any, List
from pipeline.gemini_service import GeminiService
from services.tracker import Tracker

logger = logging.getLogger(__name__)

class FlightResearcher:
    def __init__(self, gemini: GeminiService, run_id: str):
        self.gemini = gemini
        self.run_id = run_id
        self.name = "FlightResearcher"

    def execute(self, user_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        origin = user_input.get("origin", "Origin")
        destination = user_input.get("destination", "Destination")
        dep_date = user_input.get("departure_date", "")
        budget = user_input.get("budget", 1000)

        prompt = f"""
You are a specialized FlightResearcher agent.
Find 3 realistic flight or transit options from {origin} to {destination}.
Departure date: {dep_date if dep_date else 'Flexible'}.
Overall trip budget: ${budget}.

Respond ONLY with a valid JSON array containing objects with these exact keys:
- "carrier": airline or operator name
- "route": "Direct" or "1-Stop via [City]"
- "travel_time_hours": estimated travel duration in hours (number)
- "estimated_cost": estimated round-trip ticket price in USD (number)
- "departure": time of day or schedule note
- "tier": "Budget Economy", "Standard Economy", or "Premium"
"""
        Tracker.record_event(
            self.run_id,
            "agent_request",
            self.name,
            f"Searching transit options from {origin} to {destination}",
            {"origin": origin, "destination": destination, "budget": budget, "departure_date": dep_date}
        )

        resp_text = self.gemini.generate_content(prompt, agent_source=self.name)
        flights = self._parse_json(resp_text)
        if not flights:
            # Fallback realistic flight research
            flights = [
                {"carrier": "AeroDirect", "route": "Direct", "travel_time_hours": 4.5, "estimated_cost": round(budget * 0.28, 2), "departure": "09:00 AM", "tier": "Standard Economy"},
                {"carrier": "BudgetWings", "route": "1-Stop", "travel_time_hours": 6.5, "estimated_cost": round(budget * 0.18, 2), "departure": "06:15 AM", "tier": "Budget Economy"},
                {"carrier": "SkyComfort", "route": "Direct", "travel_time_hours": 4.5, "estimated_cost": round(budget * 0.38, 2), "departure": "01:30 PM", "tier": "Premium Economy"}
            ]

        Tracker.record_event(
            self.run_id,
            "agent_response",
            self.name,
            f"Identified {len(flights)} transport options for {destination}",
            {
                "flights": flights,
                "raw_model_response": resp_text
            }
        )
        return flights

    def _parse_json(self, text: str) -> List[Dict[str, Any]]:
        try:
            cleaned = text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            parsed = json.loads(cleaned.strip())
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return []


class HotelResearcher:
    def __init__(self, gemini: GeminiService, run_id: str):
        self.gemini = gemini
        self.run_id = run_id
        self.name = "HotelResearcher"

    def execute(self, user_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        destination = user_input.get("destination", "Destination")
        days = user_input.get("days", 3)
        budget = user_input.get("budget", 1000)
        interests = user_input.get("interests", [])

        prompt = f"""
You are a specialized HotelResearcher agent.
Find 3 realistic hotel / lodging options in {destination} suitable for a {days}-day stay.
Traveler interests: {', '.join(interests) if interests else 'General sightseeing'}.
Total trip budget: ${budget}.

Respond ONLY with a valid JSON array containing objects with these exact keys:
- "name": hotel or boutique stay name
- "neighborhood": neighborhood or area name in {destination}
- "safety_rating": neighborhood safety assessment (e.g. "4.8/5", "Very Safe")
- "nightly_rate": estimated cost per night in USD (number)
- "tier": e.g. "Budget Hostel/Inn", "Comfort 3-Star", "Boutique 4-Star", or "Luxury"
- "highlights": short 1-sentence note why it matches interests or safety
"""
        Tracker.record_event(
            self.run_id,
            "agent_request",
            self.name,
            f"Researching accommodations in {destination} for {days} nights",
            {"destination": destination, "days": days, "interests": interests, "budget": budget}
        )

        resp_text = self.gemini.generate_content(prompt, agent_source=self.name)
        hotels = self._parse_json(resp_text)
        if not hotels:
            target_nightly = max(35.0, (budget * 0.35) / max(1, days))
            hotels = [
                {"name": f"{destination} City Center Suites", "neighborhood": "Central Plaza", "safety_rating": "4.9/5 (Very High)", "nightly_rate": round(target_nightly * 1.1, 2), "tier": "Comfort 3-Star", "highlights": "Central location with 24/7 security and walking access to sights."},
                {"name": f"Old Town Heritage Inn", "neighborhood": "Historic District", "safety_rating": "4.8/5 (High)", "nightly_rate": round(target_nightly * 0.75, 2), "tier": "Boutique Budget", "highlights": "Charming cobblestone neighborhood near vibrant cafes."},
                {"name": f"Metro Haven Lodge", "neighborhood": "Riverside Arts Quarter", "safety_rating": "4.6/5 (Safe)", "nightly_rate": round(target_nightly * 0.5, 2), "tier": "Budget Traveler", "highlights": "Efficient modern transit connection and safe pedestrian streets."}
            ]

        Tracker.record_event(
            self.run_id,
            "agent_response",
            self.name,
            f"Found {len(hotels)} accommodation options for {destination}",
            {
                "hotels": hotels,
                "raw_model_response": resp_text
            }
        )
        return hotels

    def _parse_json(self, text: str) -> List[Dict[str, Any]]:
        try:
            cleaned = text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            parsed = json.loads(cleaned.strip())
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return []


class ActivityPlanner:
    def __init__(self, gemini: GeminiService, run_id: str):
        self.gemini = gemini
        self.run_id = run_id
        self.name = "ActivityPlanner"

    def execute(self, user_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        destination = user_input.get("destination", "Destination")
        days = user_input.get("days", 3)
        interests = user_input.get("interests", [])
        budget = user_input.get("budget", 1000)

        prompt = f"""
You are a specialized ActivityPlanner agent.
Compile top attractions, landmarks, and authentic meal dining experiences (including breakfast cafes, lunch spots, and dinner dining) for {destination}.
Duration: {days} days.
Interests: {', '.join(interests) if interests else 'Culture, Food, Sights'}.
Budget: ${budget}.

Group activities into distinct geographic areas/neighborhoods to minimize travel time between them.
Respond ONLY with a valid JSON array containing objects with these exact keys:
- "name": attraction or restaurant/cafe name
- "neighborhood": geographic neighborhood / district in {destination}
- "location": specific address, street, or landmark location in {destination}
- "category": e.g. "Breakfast", "Lunch", "Dinner", "Landmark", "Museum", "Food & Dining", "Culture", "Outdoor & Park", or "Hidden Gem"
- "estimated_cost": estimated ticket or meal price in USD (number, use 0 for free sights)
- "duration_hours": estimated time needed (number, e.g. 1.0, 1.5, 2.0)
- "description": brief description of what to see or eat, including specialty dishes or features
"""
        Tracker.record_event(
            self.run_id,
            "agent_request",
            self.name,
            f"Compiling activities, landmarks, and dining recommendations in {destination}",
            {"destination": destination, "interests": interests, "days": days, "budget": budget}
        )

        resp_text = self.gemini.generate_content(prompt, agent_source=self.name)
        activities = self._parse_json(resp_text)
        if not activities:
            activities = [
                {"name": f"{destination} Artisan Bakery & Morning Cafe", "neighborhood": "Old Town", "location": f"Main Market Square, Old Town, {destination}", "category": "Breakfast", "estimated_cost": 12.0, "duration_hours": 1.0, "description": "Freshly baked morning breads, local pastries, and specialty espresso."},
                {"name": f"{destination} Historic Old Town Walking Tour", "neighborhood": "Old Town", "location": f"Historic Center, {destination}", "category": "Culture", "estimated_cost": 0.0, "duration_hours": 2.0, "description": "Explore cobblestone alleys, historic architecture, and artisan shops."},
                {"name": "Old Town Heritage Trattoria", "neighborhood": "Old Town", "location": f"Via San Marco, Old Town, {destination}", "category": "Lunch", "estimated_cost": 22.0, "duration_hours": 1.0, "description": "Traditional lunch menu featuring regional handmade pasta and seasonal produce."},
                {"name": f"Grand Cathedral & Belfry Tower", "neighborhood": "Old Town", "location": f"Cathedral Plaza, Old Town, {destination}", "category": "Landmark", "estimated_cost": 15.0, "duration_hours": 1.5, "description": "Iconic cathedral with panoramic city views from the tower."},
                {"name": "Old Town Cellar & Grill Dinner", "neighborhood": "Old Town", "location": f"Lantern Lane, Old Town, {destination}", "category": "Dinner", "estimated_cost": 36.0, "duration_hours": 2.0, "description": "Cozy candlelight dinner serving authentic signature regional dishes and wines."},
                {"name": "Morning Espresso & Botanical Cafe", "neighborhood": "Museum Quarter", "location": f"Avenue des Arts, Museum Quarter, {destination}", "category": "Breakfast", "estimated_cost": 10.0, "duration_hours": 1.0, "description": "Light artisan breakfast overlooking the city botanical grounds."},
                {"name": f"{destination} National Art & Heritage Museum", "neighborhood": "Museum Quarter", "location": f"Museum Plaza, {destination}", "category": "Museum", "estimated_cost": 18.0, "duration_hours": 2.5, "description": "Masterpieces, historical artifacts, and immersive exhibitions."},
                {"name": "Museum Quarter Brasserie", "neighborhood": "Museum Quarter", "location": f"Boulevard Royale, Museum Quarter, {destination}", "category": "Lunch", "estimated_cost": 20.0, "duration_hours": 1.0, "description": "Vibrant terrace brasserie with gourmet sandwiches, salads, and artisan ciders."},
                {"name": "Botanical Gardens & Tea Pavilion", "neighborhood": "Museum Quarter", "location": f"Gardens North Gate, {destination}", "category": "Outdoor & Park", "estimated_cost": 8.0, "duration_hours": 1.5, "description": "Peaceful gardens with exotic flora and historic greenhouse."},
                {"name": "Museum Quarter Gastropub", "neighborhood": "Museum Quarter", "location": f"Gallery Walk, Museum Quarter, {destination}", "category": "Dinner", "estimated_cost": 32.0, "duration_hours": 2.0, "description": "Craft local brews and inventive farm-to-table dinner plates."},
                {"name": "Harborfront Breakfast Bakery", "neighborhood": "Waterfront", "location": f"Pier 4 Promenade, Waterfront, {destination}", "category": "Breakfast", "estimated_cost": 12.0, "duration_hours": 1.0, "description": "Sunrise harbor views with fresh fruit bowls and warm breakfast pastries."},
                {"name": "Scenic Riverfront Promenade & Lookout", "neighborhood": "Waterfront", "location": f"Riverside Walkway, {destination}", "category": "Sightseeing", "estimated_cost": 0.0, "duration_hours": 1.5, "description": "Relaxing stroll along the water with panoramic city skyline views."},
                {"name": "Waterfront Catch & Oyster Bar", "neighborhood": "Waterfront", "location": f"Marina Esplanade, Waterfront, {destination}", "category": "Lunch", "estimated_cost": 25.0, "duration_hours": 1.0, "description": "Fresh maritime lunch with regional catch of the day and chilled drinks."},
                {"name": "Maritime History Harbor Cruise", "neighborhood": "Waterfront", "location": f"Ferry Terminal 2, Waterfront, {destination}", "category": "Culture", "estimated_cost": 22.0, "duration_hours": 1.5, "description": "Guided scenic cruise narrating the port city's trade and nautical history."},
                {"name": "Sunset Pier Seafood & Grill Dinner", "neighborhood": "Waterfront", "location": f"Old Dockway, Waterfront, {destination}", "category": "Dinner", "estimated_cost": 42.0, "duration_hours": 2.0, "description": "Fresh regional seafood overlooking the illuminated harbor."}
            ]

        Tracker.record_event(
            self.run_id,
            "agent_response",
            self.name,
            f"Compiled {len(activities)} activities clustered across neighborhoods",
            {
                "activities": activities,
                "raw_model_response": resp_text
            }
        )
        return activities

    def _parse_json(self, text: str) -> List[Dict[str, Any]]:
        try:
            cleaned = text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            parsed = json.loads(cleaned.strip())
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return []


class ParallelAgent:
    """Orchestrator for the Discovery Phase. Runs researchers concurrently."""
    def __init__(self, gemini: GeminiService, run_id: str):
        self.gemini = gemini
        self.run_id = run_id
        self.flight_researcher = FlightResearcher(gemini, run_id)
        self.hotel_researcher = HotelResearcher(gemini, run_id)
        self.activity_planner = ActivityPlanner(gemini, run_id)

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        user_input = state["user_input"]
        Tracker.record_event(
            self.run_id,
            "agent_request",
            "ParallelAgent",
            "Starting parallel discovery phase for transport, lodging, and activities",
            {"user_input": user_input}
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            flight_future = executor.submit(self.flight_researcher.execute, user_input)
            hotel_future = executor.submit(self.hotel_researcher.execute, user_input)
            activity_future = executor.submit(self.activity_planner.execute, user_input)

            flights = flight_future.result()
            hotels = hotel_future.result()
            activities = activity_future.result()

        state["raw_research"]["flights"] = flights
        state["raw_research"]["hotels"] = hotels
        state["raw_research"]["activities"] = activities

        Tracker.record_event(
            self.run_id,
            "agent_response",
            "ParallelAgent",
            f"Completed discovery phase: {len(flights)} flights, {len(hotels)} hotels, {len(activities)} activities found",
            {
                "flights_count": len(flights),
                "hotels_count": len(hotels),
                "activities_count": len(activities),
                "flights": flights,
                "hotels": hotels,
                "activities": activities
            }
        )
        return state
