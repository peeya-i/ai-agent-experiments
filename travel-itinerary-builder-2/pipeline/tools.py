"""Tools for geographic clustering and budgetary calculations with event tracking."""
import logging
from typing import Dict, Any, List
from services.tracker import Tracker

logger = logging.getLogger(__name__)

class GeoClusteringTool:
    """Tool to group activities geographically by neighborhood to eliminate excessive transit."""
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.name = "Tool:GeoCluster"

    def execute(
        self,
        activities: List[Dict[str, Any]],
        days: int,
        destination: str
    ) -> Dict[str, Any]:
        Tracker.record_event(
            self.run_id,
            "tool_request",
            self.name,
            f"Clustering {len(activities)} activities geographically for {days} days in {destination}",
            {
                "tool": "GeoClusteringTool",
                "destination": destination,
                "days": days,
                "activities_count": len(activities),
                "activities": activities
            }
        )

        neighborhood_groups: Dict[str, List[Dict[str, Any]]] = {}
        for act in activities:
            nb = act.get("neighborhood", "Downtown / City Center")
            if nb not in neighborhood_groups:
                neighborhood_groups[nb] = []
            neighborhood_groups[nb].append(act)

        sorted_neighborhoods = sorted(
            neighborhood_groups.keys(),
            key=lambda k: len(neighborhood_groups[k]),
            reverse=True
        )

        daily_clusters = []
        for d in range(1, days + 1):
            day_nb = sorted_neighborhoods[(d - 1) % len(sorted_neighborhoods)] if sorted_neighborhoods else "Central District"
            day_pool = neighborhood_groups.get(day_nb, [])

            # Categorize activities in this neighborhood
            breakfast_candidates = [a for a in day_pool if a.get("category", "").lower() == "breakfast" or "breakfast" in a.get("name", "").lower()]
            lunch_candidates = [a for a in day_pool if a.get("category", "").lower() == "lunch" or "lunch" in a.get("name", "").lower()]
            dinner_candidates = [a for a in day_pool if a.get("category", "").lower() == "dinner" or "dinner" in a.get("name", "").lower()]
            attraction_candidates = [a for a in day_pool if a not in breakfast_candidates and a not in lunch_candidates and a not in dinner_candidates]

            day_events = []

            # 1. Breakfast Meal
            if breakfast_candidates:
                bf = dict(breakfast_candidates[0])
            else:
                bf = {
                    "name": f"{day_nb} Artisan Bakery & Morning Espresso",
                    "category": "Breakfast",
                    "location": f"Main Plaza, {day_nb}, {destination}",
                    "estimated_cost": 12.0,
                    "duration_hours": 1.0,
                    "description": "Start the day with fresh regional pastries, organic espresso, and local breakfast dishes."
                }
            bf["time_slot"] = "Breakfast (08:30 AM - 09:30 AM)"
            bf["location"] = bf.get("location") or f"Piazza Centrale, {day_nb}, {destination}"
            bf["duration_hours"] = float(bf.get("duration_hours", 1.0))
            bf["estimated_cost"] = float(bf.get("estimated_cost", 12.0))
            day_events.append(bf)

            # 2. Morning Sightseeing / Landmark
            if attraction_candidates:
                m_act = dict(attraction_candidates[0])
            else:
                m_act = {
                    "name": f"{day_nb} Historic Landmark & Walking Tour",
                    "category": "Landmark",
                    "location": f"Old Town Corridor, {day_nb}, {destination}",
                    "estimated_cost": 0.0,
                    "duration_hours": 2.0,
                    "description": f"Immerse in the iconic architecture and historic heritage of {day_nb}."
                }
            m_act["time_slot"] = "Morning Sightseeing (10:00 AM - 12:30 PM)"
            m_act["location"] = m_act.get("location") or f"Historic Quarter, {day_nb}, {destination}"
            m_act["duration_hours"] = float(m_act.get("duration_hours", 2.0))
            m_act["estimated_cost"] = float(m_act.get("estimated_cost", 0.0))
            day_events.append(m_act)

            # 3. Lunch Meal
            if lunch_candidates:
                lunch = dict(lunch_candidates[0])
            else:
                lunch = {
                    "name": f"{day_nb} Regional Market Bistro & Lunch",
                    "category": "Lunch",
                    "location": f"Market Hall, {day_nb}, {destination}",
                    "estimated_cost": 22.0,
                    "duration_hours": 1.0,
                    "description": "Midday meal highlighting local artisan ingredients, regional specialties, and seasonal salads."
                }
            lunch["time_slot"] = "Lunch (01:00 PM - 02:00 PM)"
            lunch["location"] = lunch.get("location") or f"Via del Mercato, {day_nb}, {destination}"
            lunch["duration_hours"] = float(lunch.get("duration_hours", 1.0))
            lunch["estimated_cost"] = float(lunch.get("estimated_cost", 22.0))
            day_events.append(lunch)

            # 4. Afternoon Activity
            if len(attraction_candidates) > 1:
                af_act = dict(attraction_candidates[1])
            else:
                af_act = {
                    "name": f"{day_nb} National Arts & Heritage Exhibition",
                    "category": "Culture",
                    "location": f"Museum Walk, {day_nb}, {destination}",
                    "estimated_cost": 15.0,
                    "duration_hours": 2.5,
                    "description": f"Curated cultural galleries showcasing regional art, history, and craft traditions."
                }
            af_act["time_slot"] = "Afternoon Exploration (02:30 PM - 05:00 PM)"
            af_act["location"] = af_act.get("location") or f"Avenue of the Arts, {day_nb}, {destination}"
            af_act["duration_hours"] = float(af_act.get("duration_hours", 2.5))
            af_act["estimated_cost"] = float(af_act.get("estimated_cost", 15.0))
            day_events.append(af_act)

            # 5. Dinner Meal
            if dinner_candidates:
                dinner = dict(dinner_candidates[0])
            else:
                dinner = {
                    "name": f"{day_nb} Traditional Gastronomy & Wine Dinner",
                    "category": "Dinner",
                    "location": f"Riverside Promenade, {day_nb}, {destination}",
                    "estimated_cost": 38.0,
                    "duration_hours": 2.0,
                    "description": "Atmospheric evening dining experience featuring traditional dinner courses and regional wine."
                }
            dinner["time_slot"] = "Dinner (07:00 PM - 09:00 PM)"
            dinner["location"] = dinner.get("location") or f"Harbor Walk, {day_nb}, {destination}"
            dinner["duration_hours"] = float(dinner.get("duration_hours", 2.0))
            dinner["estimated_cost"] = float(dinner.get("estimated_cost", 38.0))
            day_events.append(dinner)

            # Calculate total estimated cost for this day
            day_cost = round(sum(float(e.get("estimated_cost", 0.0)) for e in day_events), 2)

            daily_clusters.append({
                "day": d,
                "estimated_cost": day_cost,
                "neighborhood_focus": day_nb,
                "events": day_events
            })

        result = {
            "destination": destination,
            "days": days,
            "neighborhoods_identified": list(neighborhood_groups.keys()),
            "daily_clusters": daily_clusters
        }

        Tracker.record_event(
            self.run_id,
            "tool_response",
            self.name,
            f"Successfully clustered activities into {len(daily_clusters)} daily geographic zones",
            {
                "tool": "GeoClusteringTool",
                "result": result
            }
        )

        return result


class BudgetCalculatorTool:
    """Tool to calculate total trip expenses across transit, accommodation, and daily activities."""
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.name = "Tool:BudgetCalculator"

    def execute(
        self,
        flight: Dict[str, Any],
        hotel: Dict[str, Any],
        days: int,
        schedule: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        Tracker.record_event(
            self.run_id,
            "tool_request",
            self.name,
            f"Calculating detailed budget breakdown for {days}-day itinerary",
            {
                "tool": "BudgetCalculatorTool",
                "flight": flight,
                "hotel": hotel,
                "days": days,
                "schedule_days_count": len(schedule)
            }
        )

        flight_cost = float(flight.get("estimated_cost", 0.0))
        nightly_rate = float(hotel.get("nightly_rate", 0.0))
        hotel_total = round(nightly_rate * days, 2)

        activities_total = 0.0
        for day in schedule:
            for ev in day.get("events", []):
                activities_total += float(ev.get("estimated_cost", 0.0))

        activities_total = round(activities_total, 2)
        total_cost = round(flight_cost + hotel_total + activities_total, 2)

        breakdown = {
            "flight": flight_cost,
            "lodging": hotel_total,
            "activities": activities_total,
            "total_estimated_cost": total_cost
        }

        Tracker.record_event(
            self.run_id,
            "tool_response",
            self.name,
            f"Budget calculation complete. Total: ${total_cost:.2f} (Flights: ${flight_cost:.2f}, Hotel: ${hotel_total:.2f}, Activities: ${activities_total:.2f})",
            {
                "tool": "BudgetCalculatorTool",
                "breakdown": breakdown
            }
        )

        return breakdown
