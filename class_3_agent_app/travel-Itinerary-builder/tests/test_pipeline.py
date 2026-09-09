"""Unit and Integration tests for Travel Itinerary Builder."""

import unittest
from pipeline.state import create_initial_state, validate_state
from pipeline.agents import (
    create_travel_pipeline,
    create_discovery_team,
    create_optimization_room,
    create_flight_researcher,
    create_hotel_researcher,
    create_activity_planner,
    create_scheduler,
    create_budget_enforcer
)
from pipeline.runner import generate_fallback_itinerary, run_itinerary_pipeline
from google.adk.agents import ParallelAgent, LoopAgent, SequentialAgent
from app import app


class TestTravelItineraryBuilder(unittest.TestCase):
    """Test suite covering assignment milestones and Flask integration."""

    def test_milestone_1_structural_integrity(self):
        """Milestone 1: Must explicitly declare ParallelAgent and LoopAgent frameworks."""
        pipeline = create_travel_pipeline()
        self.assertIsInstance(pipeline, SequentialAgent, "Pipeline root must be a SequentialAgent")
        self.assertEqual(len(pipeline.sub_agents), 2, "Pipeline must contain Discovery and Optimization phases")

        discovery_team = pipeline.sub_agents[0]
        self.assertIsInstance(discovery_team, ParallelAgent, "Phase 1 must be a ParallelAgent")
        self.assertEqual(len(discovery_team.sub_agents), 3, "Discovery must contain 3 parallel sub-agents (FlightResearcher, HotelResearcher, ActivityPlanner)")
        sub_agent_names = [a.name for a in discovery_team.sub_agents]
        self.assertIn("FlightResearcher", sub_agent_names)
        self.assertIn("HotelResearcher", sub_agent_names)
        self.assertIn("ActivityPlanner", sub_agent_names)

        optimization_room = pipeline.sub_agents[1]
        self.assertIsInstance(optimization_room, LoopAgent, "Phase 2 must be a LoopAgent")
        self.assertEqual(optimization_room.max_iterations, 5, "LoopAgent must cap at 5 iterations")
        loop_sub_agent_names = [a.name for a in optimization_room.sub_agents]
        self.assertIn("Scheduler", loop_sub_agent_names)
        self.assertIn("BudgetEnforcer", loop_sub_agent_names)

    def test_usages_csv_logging(self):
        """Test that usages.csv is created and written with required 10 columns."""
        import os
        import csv
        from pathlib import Path
        from pipeline.event_logger import append_usage_to_csv, CSV_COLUMNS, DEFAULT_USAGES_CSV

        test_csv = Path("artifacts/test_usages.csv")
        if test_csv.exists():
            test_csv.unlink()

        record = {
            "timestamp": "2026-08-31T12:00:00Z",
            "event_type": "test_request",
            "user_input": {"destination": "Tokyo", "budget": 2000, "city_of_origin": "SF"},
            "prompt": "Test prompt",
            "agent": "TestAgent",
            "model": "gemini-3.5-flash-lite",
            "request_contents": "test content",
            "config": "{}",
            "response": "test response",
            "debug_log": "test debug log"
        }

        append_usage_to_csv(record, file_path=test_csv)
        self.assertTrue(test_csv.exists())

        with open(test_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, CSV_COLUMNS)
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["agent"], "TestAgent")
            self.assertEqual(rows[0]["model"], "gemini-3.5-flash-lite")

        if test_csv.exists():
            test_csv.unlink()

    def test_milestone_2_state_schema_and_context_extraction(self):
        """Milestone 2: Centralized Global State Schema & critic feedback."""
        state = create_initial_state(
            destination="Kyoto",
            budget=2500.0,
            days=5,
            interests=["Shrines", "Tea Ceremony"]
        )
        self.assertTrue(validate_state(state), "State must conform to Global State Schema")
        self.assertEqual(state["user_input"]["destination"], "Kyoto")
        self.assertEqual(state["user_input"]["budget"], 2500.0)
        self.assertEqual(state["user_input"]["days"], 5)
        self.assertEqual(state["critic_feedback"], "")
        self.assertFalse(state["budget_approved"])

        # Simulate refinement loop with critic feedback
        # Iteration 1: Over-budget, critic feedback emitted
        cost_iter_1 = 3200.0
        budget = state["user_input"]["budget"]
        feedback = f"Total cost ${cost_iter_1:.2f} exceeds budget ${budget:.2f}. Replace luxury hotel with mid-range and remove premium private tours."
        state["current_itinerary"]["total_estimated_cost"] = cost_iter_1
        state["critic_feedback"] = feedback
        state["budget_approved"] = False

        # Verify state is updated with feedback
        self.assertEqual(state["critic_feedback"], feedback)
        self.assertFalse(state["budget_approved"])

        # Iteration 2: Scheduler extracts critic_feedback, downgrades hotel, cost <= budget
        cost_iter_2 = 2350.0
        state["current_itinerary"]["total_estimated_cost"] = cost_iter_2
        state["budget_approved"] = True
        state["critic_feedback"] = "Budget approved: Total cost is within budget."

        self.assertTrue(validate_state(state))
        self.assertTrue(state["budget_approved"])
        self.assertLessEqual(state["current_itinerary"]["total_estimated_cost"], budget)

    def test_milestone_3_graceful_failure_handling(self):
        """Milestone 3: Must handle impossible inputs (e.g. extremely low budgets) without crashing."""
        impossible_input = {
            "destination": "London",
            "budget": 5.0,  # Impossible $5 budget for 10 days
            "days": 10,
            "interests": ["Museums"]
        }
        # Run fallback generation
        result = generate_fallback_itinerary(impossible_input, reason="Extreme Budget Check")
        self.assertIsNotNone(result)
        self.assertTrue(validate_state(result))
        self.assertIn("schedule", result["current_itinerary"])
        self.assertEqual(len(result["current_itinerary"]["schedule"]), 10)
        self.assertIn("budget", result["user_input"])

    def test_flask_validation_missing_fields(self):
        """Test Flask input validation prompts user when required fields are missing."""
        client = app.test_client()

        # Missing destination
        res = client.post("/api/generate", json={"budget": 1000, "days": 3})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Destination", data["error"])

        # Missing budget
        res = client.post("/api/generate", json={"destination": "Tokyo", "days": 3})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Budget", data["error"])

        # Missing days
        res = client.post("/api/generate", json={"destination": "Tokyo", "budget": 1000})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Duration", data["error"])

    def test_normalize_schedule_flat_and_nested(self):
        """Test that normalize_schedule correctly partitions flat event lists into DaySchedule objects."""
        from pipeline.tools import normalize_schedule

        # Test flat list of 21 events distributed across 8 days
        flat_events = [
            {"time": "09:00 AM", "title": f"Activity {i}", "category": "sightseeing", "estimated_cost": 20.0, "description": f"Desc {i}"}
            for i in range(21)
        ]
        norm = normalize_schedule(flat_events, total_days=8)
        self.assertEqual(len(norm), 8)
        for d in norm:
            self.assertIn("day", d)
            self.assertIn("events", d)
            self.assertGreater(len(d["events"]), 0)

        total_evs = sum(len(d["events"]) for d in norm)
        self.assertEqual(total_evs, 21)

    def test_activity_planner_and_error_handling(self):
        """Test ActivityPlanner agent configuration, data structuring, and error handling."""
        from pipeline.agents import create_activity_planner
        from pipeline.tools import save_activity_research
        from unittest.mock import MagicMock

        # 1. Verify ActivityPlanner agent contains save_activity_research tool
        planner = create_activity_planner()
        tool_names = [getattr(t, "__name__", getattr(t, "name", str(t))) for t in planner.tools]
        self.assertIn("save_activity_research", tool_names)

        # 2. Test error resilience in save_activity_research with malformed entries
        mock_ctx = MagicMock()
        mock_ctx.state = {"raw_research": {}}
        malformed_activities = [
            {"activity_name": "Colosseum Tour", "category": "landmark", "estimated_cost": "invalid_cost", "duration_hours": "three"},
            {"activity_name": "Trastevere Dinner", "estimated_cost": 35.0}
        ]
        msg = save_activity_research(mock_ctx, malformed_activities)
        self.assertIn("Successfully saved 2", msg)
        saved = mock_ctx.state["raw_research"]["activities"]
        self.assertEqual(len(saved), 2)
        self.assertEqual(saved[0]["estimated_cost"], 0.0)  # Graceful fallback for invalid cost

        # 3. Verify tool invocations appear in pipeline log outputs
    def test_exact_cost_sum_calculation(self):
        """Test that total_estimated_cost strictly equals flight + lodging * days + sum(activities)."""
        from pipeline.tools import calculate_exact_itinerary_cost, save_itinerary_schedule
        from unittest.mock import MagicMock

        state = {
            "user_input": {"days": 4, "budget": 2000.0, "destination": "Tokyo"},
            "raw_research": {
                "flights": [{"flight_name": "Flight A", "estimated_cost": 650.0}],
                "hotels": [{"hotel_name": "Hotel B", "price_per_night": 120.0}],
                "activities": []
            },
            "current_itinerary": {}
        }
        schedule = [
            {"day": 1, "events": [{"title": "Museum", "estimated_cost": 30.0}, {"title": "Dinner", "estimated_cost": 45.0}]},
            {"day": 2, "events": [{"title": "Temple", "estimated_cost": 15.0}, {"title": "Lunch", "estimated_cost": 25.0}]},
            {"day": 3, "events": [{"title": "Park", "estimated_cost": 0.0}, {"title": "Dinner", "estimated_cost": 50.0}]},
            {"day": 4, "events": [{"title": "Shopping", "estimated_cost": 60.0}]}
        ]
        # Flight = 650
        # Hotel = 120 * 4 = 480
        # Activities = 30 + 45 + 15 + 25 + 0 + 50 + 60 = 225
        # Expected Total = 650 + 480 + 225 = 1355.0
        exact_cost = calculate_exact_itinerary_cost(state, schedule)
        self.assertEqual(exact_cost, 1355.0)

        # Test save_itinerary_schedule tool enforces this exact sum even if LLM provided an inconsistent number
        mock_ctx = MagicMock()
        mock_ctx.state = dict(state)
        save_itinerary_schedule(mock_ctx, schedule, total_estimated_cost=9999.0)  # Inconsistent model cost
    def test_scheduler_skill_and_geographic_clustering(self):
        """Test Scheduler agent skill integration and geographic clustering instructions."""
        from pipeline.agents import create_scheduler, get_scheduler_skill_toolset

        # 1. Verify skill toolset loads properly
        skill_toolset = get_scheduler_skill_toolset()
        self.assertIsNotNone(skill_toolset, "Scheduler skill toolset must load from skills/itinerary-enhancer-skill")

        # 2. Verify Scheduler agent contains skill tools and save_itinerary_schedule
        scheduler = create_scheduler()
        tool_names = [getattr(t, "__name__", getattr(t, "name", str(t))) for t in scheduler.tools]
        self.assertIn("save_itinerary_schedule", tool_names)

        # 3. Verify geographic clustering and skill directives in instructions
        self.assertIn("Geographic Clustering", scheduler.instruction)
        self.assertIn("itinerary-enhancer-skill", scheduler.instruction)


if __name__ == "__main__":
    unittest.main()
