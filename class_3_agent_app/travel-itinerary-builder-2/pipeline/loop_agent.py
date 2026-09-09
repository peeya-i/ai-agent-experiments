"""Loop Agent framework orchestrating iterative refinement between Scheduler and BudgetEnforcer."""
import logging
from typing import Dict, Any, List
from pipeline.gemini_service import GeminiService
from pipeline.skills import LocalVibeSkill, HiddenGemSkill
from pipeline.tools import GeoClusteringTool, BudgetCalculatorTool
from services.tracker import Tracker

logger = logging.getLogger(__name__)

class Scheduler:
    """Reads research, incorporates critic_feedback, groups daily activities geographically, and calculates total costs."""
    def __init__(self, gemini: GeminiService, run_id: str):
        self.gemini = gemini
        self.run_id = run_id
        self.name = "Scheduler"
        self.local_vibe_skill = LocalVibeSkill(gemini, run_id)
        self.hidden_gem_skill = HiddenGemSkill(gemini, run_id)
        self.geo_tool = GeoClusteringTool(run_id)
        self.calculator_tool = BudgetCalculatorTool(run_id)

    def execute(self, state: Dict[str, Any], iteration: int) -> Dict[str, Any]:
        user_input = state["user_input"]
        raw_research = state["raw_research"]
        critic_feedback = state.get("critic_feedback", "")
        days = max(1, user_input.get("days", 3))
        destination = user_input.get("destination", "Destination")
        budget = float(user_input.get("budget", 1000.0))
        interests = user_input.get("interests", [])

        Tracker.record_event(
            self.run_id,
            "agent_request",
            self.name,
            f"Scheduler starting iteration {iteration} (Feedback applied: {'Yes' if critic_feedback else 'No'})",
            {"iteration": iteration, "destination": destination, "days": days, "budget": budget, "critic_feedback": critic_feedback}
        )

        flights = raw_research.get("flights", [])
        hotels = raw_research.get("hotels", [])
        activities = raw_research.get("activities", [])

        # 1. Select Transport option based on iteration & feedback
        selected_flight = self._select_flight(flights, iteration, critic_feedback, budget)

        # 2. Select Hotel option based on iteration & feedback
        selected_hotel = self._select_hotel(hotels, iteration, critic_feedback, days, budget)

        # 3. Filter / Adjust activities based on iteration & feedback
        active_activities = self._filter_activities(activities, iteration, critic_feedback)

        # 4. Group activities geographically by day using GeoClusteringTool
        cluster_data = self.geo_tool.execute(active_activities, days, destination)
        base_schedule = cluster_data.get("daily_clusters", [])

        # 5. Enrich daily schedule with Gemini skills
        schedule = self._enrich_schedule_with_skills(base_schedule, days, destination, interests)

        # 6. Calculate Total Costs using BudgetCalculatorTool
        cost_breakdown = self.calculator_tool.execute(selected_flight, selected_hotel, days, schedule)
        total_cost = cost_breakdown["total_estimated_cost"]

        # Update state current_itinerary
        state["current_itinerary"] = {
            "destination": destination,
            "days": days,
            "selected_flight": selected_flight,
            "selected_hotel": selected_hotel,
            "total_estimated_cost": total_cost,
            "cost_breakdown": {
                "flight": cost_breakdown["flight"],
                "lodging": cost_breakdown["lodging"],
                "activities": cost_breakdown["activities"]
            },
            "schedule": schedule,
            "iteration": iteration
        }

        Tracker.record_event(
            self.run_id,
            "agent_response",
            self.name,
            f"Scheduler compiled day-by-day plan for iteration {iteration}. Total cost: ${total_cost:.2f}",
            {
                "iteration": iteration,
                "total_estimated_cost": total_cost,
                "cost_breakdown": state["current_itinerary"]["cost_breakdown"],
                "flight": selected_flight.get("carrier"),
                "hotel": selected_hotel.get("name"),
                "schedule": schedule
            }
        )
        return state

    def _select_flight(self, flights: List[Dict[str, Any]], iteration: int, feedback: str, budget: float) -> Dict[str, Any]:
        if not flights:
            return {"carrier": "Standard Airline", "estimated_cost": round(budget * 0.25, 2), "tier": "Economy"}
        # Sort flights by price ascending
        sorted_flights = sorted(flights, key=lambda f: float(f.get("estimated_cost", 99999)))
        if iteration > 1 or "cheaper" in feedback.lower() or "flight" in feedback.lower():
            # Choose lowest price flight
            return sorted_flights[0]
        # On first iteration, pick middle / standard if available
        if len(sorted_flights) > 1:
            return sorted_flights[1]
        return sorted_flights[0]

    def _select_hotel(self, hotels: List[Dict[str, Any]], iteration: int, feedback: str, days: int, budget: float) -> Dict[str, Any]:
        if not hotels:
            nightly = max(35.0, (budget * 0.3) / days)
            return {"name": "Recommended Hotel", "neighborhood": "Central", "nightly_rate": round(nightly, 2), "tier": "Comfort"}
        # Sort hotels by nightly rate ascending
        sorted_hotels = sorted(hotels, key=lambda h: float(h.get("nightly_rate", 99999)))
        if iteration >= 3:
            # Most economical
            return sorted_hotels[0]
        elif iteration == 2 or "hotel" in feedback.lower() or "downgrade" in feedback.lower():
            # Lower tier hotel
            return sorted_hotels[0]
        # First iteration: middle or comfortable option
        if len(sorted_hotels) >= 2:
            return sorted_hotels[-2]
        return sorted_hotels[0]

    def _filter_activities(self, activities: List[Dict[str, Any]], iteration: int, feedback: str) -> List[Dict[str, Any]]:
        if not activities:
            return []
        if iteration > 1 or "cost" in feedback.lower() or "free" in feedback.lower():
            # Prefer free or low-cost activities
            sorted_act = sorted(activities, key=lambda a: float(a.get("estimated_cost", 0.0)))
            return sorted_act
        return activities

    def _enrich_schedule_with_skills(
        self,
        base_schedule: List[Dict[str, Any]],
        days: int,
        destination: str,
        interests: List[str]
    ) -> List[Dict[str, Any]]:
        # Get a hidden gem via skill
        hidden_gem = self.hidden_gem_skill.execute(destination, interests)
        schedule = []

        for day_cluster in base_schedule:
            d = day_cluster.get("day", 1)
            day_nb = day_cluster.get("neighborhood_focus", "Central District")
            day_events = list(day_cluster.get("events", []))

            # Add hidden gem on Day 2 (or Day 1 if 1-day trip)
            if (d == 2 or (days == 1 and d == 1)) and hidden_gem:
                gem_event = {
                    "name": f"✨ Hidden Gem: {hidden_gem.get('title', 'Secret Spot')}",
                    "neighborhood": hidden_gem.get("neighborhood", day_nb),
                    "location": f"{hidden_gem.get('neighborhood', day_nb)}, {destination}",
                    "category": "Hidden Gem",
                    "estimated_cost": float(hidden_gem.get("estimated_cost", 0.0)),
                    "duration_hours": 1.5,
                    "description": hidden_gem.get("description", "Curated local discovery."),
                    "time_slot": "Late Afternoon (05:00 PM - 06:30 PM)"
                }
                day_events.append(gem_event)

            # Local vibe skill tip
            insider_tip = self.local_vibe_skill.execute(destination, day_nb, d)

            # Calculate total cost for the day
            day_cost = round(sum(float(e.get("estimated_cost", 0.0)) for e in day_events), 2)

            schedule.append({
                "day": d,
                "estimated_cost": day_cost,
                "neighborhood_focus": day_nb,
                "insider_tip": insider_tip,
                "events": day_events
            })

        return schedule


class BudgetEnforcer:
    """Validates the itinerary against the user's budget and produces actionable critic_feedback."""
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.name = "BudgetEnforcer"

    def execute(self, state: Dict[str, Any], iteration: int, max_iterations: int) -> bool:
        budget = float(state["user_input"].get("budget", 0.0))
        itinerary = state.get("current_itinerary", {})
        total_cost = float(itinerary.get("total_estimated_cost", 0.0))

        Tracker.record_event(
            self.run_id,
            "agent_request",
            self.name,
            f"Evaluating budget for iteration {iteration}: Cost ${total_cost:.2f} vs Budget ${budget:.2f}",
            {"iteration": iteration, "cost": total_cost, "budget": budget, "max_iterations": max_iterations}
        )

        if total_cost <= budget:
            state["budget_approved"] = True
            state["critic_feedback"] = f"Budget Approved: Total cost of ${total_cost:.2f} is within user budget of ${budget:.2f}."
            Tracker.record_event(
                self.run_id,
                "agent_response",
                self.name,
                f"Budget approved on iteration {iteration} (${total_cost:.2f} <= ${budget:.2f})",
                {"iteration": iteration, "budget_approved": True, "total_cost": total_cost, "budget": budget, "surplus": round(budget - total_cost, 2), "critic_feedback": state["critic_feedback"]}
            )
            return True
        else:
            state["budget_approved"] = False
            overage = round(total_cost - budget, 2)

            if iteration >= max_iterations:
                state["critic_feedback"] = (
                    f"Final iteration reached. Total cost (${total_cost:.2f}) exceeds budget (${budget:.2f}) by ${overage:.2f}. "
                    f"Selected the lowest available options across flights, lodging, and activities. "
                    f"Budget is structurally tight or insufficient for this destination and duration."
                )
            else:
                state["critic_feedback"] = (
                    f"Budget Exceeded: Total cost ${total_cost:.2f} exceeds target ${budget:.2f} by ${overage:.2f}. "
                    f"Critic Recommendation for Iteration {iteration + 1}: Downgrade to lower-tier lodging, "
                    f"switch to economy transit tier, and substitute paid activities with free neighborhood walking sights."
                )

            Tracker.record_event(
                self.run_id,
                "agent_response",
                self.name,
                f"Budget exceeded on iteration {iteration} (${total_cost:.2f} > ${budget:.2f}). Generating critic feedback.",
                {"iteration": iteration, "budget_approved": False, "cost": total_cost, "budget": budget, "overage": overage, "critic_feedback": state["critic_feedback"]}
            )
            return False


class LoopAgent:
    """Orchestrator for the Optimization Room. Refines itinerary iteratively up to max_iterations."""
    def __init__(self, gemini: GeminiService, run_id: str, max_iterations: int = 3):
        self.gemini = gemini
        self.run_id = run_id
        self.max_iterations = max_iterations
        self.scheduler = Scheduler(gemini, run_id)
        self.budget_enforcer = BudgetEnforcer(run_id)

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        Tracker.record_event(
            self.run_id,
            "agent_request",
            "LoopAgent",
            f"Starting iterative refinement loop (Max iterations: {self.max_iterations})",
            {"max_iterations": self.max_iterations, "target_budget": state["user_input"]["budget"]}
        )

        for iteration in range(1, self.max_iterations + 1):
            # 1. Scheduler builds/modifies the itinerary using state and any prior critic_feedback
            state = self.scheduler.execute(state, iteration)

            # 2. BudgetEnforcer checks constraints
            approved = self.budget_enforcer.execute(state, iteration, self.max_iterations)

            if approved:
                Tracker.record_event(
                    self.run_id,
                    "agent_response",
                    "LoopAgent",
                    f"Refinement loop succeeded at iteration {iteration}.",
                    {"iterations_used": iteration, "budget_approved": True, "final_cost": state["current_itinerary"]["total_estimated_cost"]}
                )
                break
            else:
                if iteration == self.max_iterations:
                    Tracker.record_event(
                        self.run_id,
                        "agent_response",
                        "LoopAgent",
                        f"Refinement loop reached max iterations ({self.max_iterations}) without reaching budget.",
                        {"iterations_used": iteration, "budget_approved": False, "final_cost": state["current_itinerary"]["total_estimated_cost"], "budget": state["user_input"]["budget"], "critic_feedback": state.get("critic_feedback")}
                    )

        return state
