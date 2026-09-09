"""Sequential Pipeline Orchestrator coordinating Discovery and Optimization."""
import uuid
import logging
from typing import Dict, Any, List, Optional
from pipeline.state import create_initial_state
from pipeline.gemini_service import GeminiService
from pipeline.parallel_agent import ParallelAgent
from pipeline.loop_agent import LoopAgent
from services.tracker import Tracker

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or f"run_{uuid.uuid4().hex[:10]}"
        self.gemini = GeminiService(self.run_id)
        self.parallel_agent = ParallelAgent(self.gemini, self.run_id)
        self.loop_agent = LoopAgent(self.gemini, self.run_id, max_iterations=3)

    def run(
        self,
        origin: str,
        destination: str,
        days: int,
        budget: float,
        interests: List[str],
        departure_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executes the full sequential multi-agent pipeline."""
        # Sanitize and safeguard inputs
        safe_days = max(1, min(int(days), 30))
        safe_budget = max(1.0, float(budget))
        safe_origin = str(origin).strip() or "City of Origin"
        safe_destination = str(destination).strip() or "Destination"

        state = create_initial_state(
            destination=safe_destination,
            budget=safe_budget,
            days=safe_days,
            interests=interests,
            origin=safe_origin,
            departure_date=departure_date
        )

        Tracker.record_event(
            self.run_id,
            "pipeline_request",
            "PipelineOrchestrator",
            f"Initialized itinerary pipeline request for {safe_destination} ({safe_days} days, budget ${safe_budget:.2f})",
            {"user_input": state["user_input"]}
        )

        try:
            # Phase 1: Parallel Discovery Phase
            state = self.parallel_agent.execute(state)

            # Phase 2: Iterative Loop Refinement Phase
            state = self.loop_agent.execute(state)

            # Check final status
            approved = state.get("budget_approved", False)
            status = "success" if approved else "budget_exceeded"

            final_cost = state.get("current_itinerary", {}).get("total_estimated_cost", 0.0)
            iterations = state.get("current_itinerary", {}).get("iteration", 1)
            events_count = len(Tracker.get_events_for_run(self.run_id))

            Tracker.record_usage(
                run_id=self.run_id,
                origin=safe_origin,
                destination=safe_destination,
                days=safe_days,
                budget=safe_budget,
                estimated_cost=final_cost,
                budget_approved=approved,
                status=status,
                iterations=iterations,
                events_count=events_count + 1,  # including the completion event
                travel_date=departure_date or "Flexible"
            )

            Tracker.save_run_itinerary(self.run_id, state)

            Tracker.record_event(
                self.run_id,
                "pipeline_response",
                "PipelineOrchestrator",
                f"Completed pipeline execution. Status: {status}, Total Cost: ${final_cost:.2f}",
                {
                    "run_id": self.run_id,
                    "status": status,
                    "final_cost": final_cost,
                    "budget_approved": approved,
                    "iterations": iterations,
                    "current_itinerary": state.get("current_itinerary")
                }
            )

            return {
                "success": True,
                "run_id": self.run_id,
                "status": status,
                "state": state
            }

        except Exception as e:
            logger.exception(f"Pipeline error for run {self.run_id}: {e}")
            Tracker.record_event(
                self.run_id,
                "pipeline_error",
                "PipelineOrchestrator",
                f"Pipeline encountered an unexpected error: {str(e)}",
                {"error": str(e)}
            )
            # Graceful failure recording in usages
            events_count = len(Tracker.get_events_for_run(self.run_id))
            Tracker.record_usage(
                run_id=self.run_id,
                origin=safe_origin,
                destination=safe_destination,
                days=safe_days,
                budget=safe_budget,
                estimated_cost=0.0,
                budget_approved=False,
                status="failed",
                iterations=0,
                events_count=events_count,
                travel_date=departure_date or "Flexible"
            )
            return {
                "success": False,
                "run_id": self.run_id,
                "status": "failed",
                "error": str(e),
                "state": state
            }
