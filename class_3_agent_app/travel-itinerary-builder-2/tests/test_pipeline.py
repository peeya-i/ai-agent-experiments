"""Automated verification suite for Travel Itinerary Builder."""
import os
import unittest
import json
import uuid
from pipeline.state import create_initial_state
from pipeline.gemini_service import GeminiService
from pipeline.parallel_agent import ParallelAgent
from pipeline.loop_agent import LoopAgent, Scheduler, BudgetEnforcer
from pipeline.orchestrator import PipelineOrchestrator
from services.tracker import Tracker
from services.export_service import generate_text_itinerary, generate_pdf_itinerary
from app import app
import config

class TestItineraryPipeline(unittest.TestCase):
    def setUp(self):
        self.run_id = "test_run_123"
        self.gemini = GeminiService(self.run_id)

    def test_global_state_schema(self):
        """Validates that Global State strictly conforms to SPECIFICATIONS.md schema."""
        state = create_initial_state(
            destination="Rome, Italy",
            budget=1500.0,
            days=4,
            interests=["Architecture", "Food"],
            origin="New York, USA"
        )
        self.assertIn("user_input", state)
        self.assertIn("raw_research", state)
        self.assertIn("current_itinerary", state)
        self.assertIn("critic_feedback", state)
        self.assertIn("budget_approved", state)

        # Check raw_research subfields
        self.assertIn("flights", state["raw_research"])
        self.assertIn("hotels", state["raw_research"])
        self.assertIn("activities", state["raw_research"])

        # Check user_input subfields
        self.assertEqual(state["user_input"]["destination"], "Rome, Italy")
        self.assertEqual(state["user_input"]["budget"], 1500.0)
        self.assertEqual(state["user_input"]["days"], 4)
        self.assertEqual(state["budget_approved"], False)

    def test_parallel_agent_execution(self):
        """Verifies ParallelAgent executes discovery concurrently and updates state."""
        state = create_initial_state(
            destination="Barcelona, Spain",
            budget=1200.0,
            days=3,
            interests=["Art", "Beach"],
            origin="London, UK"
        )
        agent = ParallelAgent(self.gemini, self.run_id)
        updated_state = agent.execute(state)

        self.assertTrue(len(updated_state["raw_research"]["flights"]) > 0)
        self.assertTrue(len(updated_state["raw_research"]["hotels"]) > 0)
        self.assertTrue(len(updated_state["raw_research"]["activities"]) > 0)

    def test_loop_agent_refinement_and_budget_approval(self):
        """Verifies LoopAgent runs Scheduler and BudgetEnforcer with critic feedback."""
        state = create_initial_state(
            destination="Paris, France",
            budget=2500.0,  # Generous budget
            days=3,
            interests=["Art", "Pastries"],
            origin="New York, USA"
        )
        # Populate mock research
        state["raw_research"]["flights"] = [
            {"carrier": "AirFrance", "route": "Direct", "travel_time_hours": 7.5, "estimated_cost": 450.0, "tier": "Economy"}
        ]
        state["raw_research"]["hotels"] = [
            {"name": "Hotel Louvre", "neighborhood": "1st Arr.", "nightly_rate": 180.0, "tier": "Comfort"}
        ]
        state["raw_research"]["activities"] = [
            {"name": "Louvre Tour", "neighborhood": "1st Arr.", "category": "Museum", "estimated_cost": 25.0, "duration_hours": 3.0}
        ]

        loop_agent = LoopAgent(self.gemini, self.run_id, max_iterations=3)
        final_state = loop_agent.execute(state)

        self.assertTrue(final_state["budget_approved"])
        self.assertIn("schedule", final_state["current_itinerary"])
        self.assertTrue(final_state["current_itinerary"]["total_estimated_cost"] <= 2500.0)

    def test_graceful_failure_handling_tight_budget(self):
        """Verifies pipeline does not crash on impossible budgets ($5 for 5 days)."""
        orchestrator = PipelineOrchestrator(run_id="impossible_budget_test")
        result = orchestrator.run(
            origin="NYC",
            destination="Tokyo, Japan",
            days=5,
            budget=5.0,  # Structurally impossible budget
            interests=["Culture"]
        )
        self.assertTrue(result["success"])  # Pipeline executed cleanly without exception
        self.assertFalse(result["state"]["budget_approved"])  # Marked as budget exceeded
        self.assertIn("tight or insufficient", result["state"]["critic_feedback"].lower())

    def test_tracker_artifact_logging(self):
        """Verifies usages.csv and events.json tracking and metric queries."""
        test_run = "tracker_test_run"
        Tracker.record_event(test_run, "test_event", "TestAgent", "Unit test summary", {"key": "val"})
        Tracker.record_usage(
            run_id=test_run,
            origin="SF",
            destination="Hawaii",
            days=4,
            budget=1500.0,
            estimated_cost=1400.0,
            budget_approved=True,
            status="success",
            iterations=1,
            events_count=3,
            travel_date="2026-10-15"
        )

        metrics = Tracker.get_metrics()
        self.assertGreaterEqual(metrics["total_itineraries"], 1)
        self.assertGreaterEqual(metrics["total_events"], 1)

        usages = Tracker.get_all_usages()
        test_usage = next((u for u in usages if u.get("run_id") == test_run), None)
        self.assertIsNotNone(test_usage)
        self.assertEqual(test_usage.get("travel_date"), "2026-10-15")

        run_events = Tracker.get_events_for_run(test_run)
        self.assertTrue(len(run_events) >= 1)
        self.assertEqual(run_events[0]["agent_source"], "TestAgent")
        self.assertEqual(run_events[0]["payload"], {"key": "val"})

        # Verify each event log in events.json is on a single line
        with open(config.EVENTS_JSON, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    ev_obj = json.loads(line_str)
                    self.assertIsInstance(ev_obj, dict)
                    self.assertIn("event_id", ev_obj)
                    self.assertIn("payload", ev_obj)

    def test_api_key_redaction_in_events(self):
        """Verifies that API keys are redacted from event payloads and summaries before saving to events.json."""
        redact_run = f"redaction_test_{uuid.uuid4().hex[:8]}"
        dummy_key = "AIzaSySecretApiKey12345XYZ"
        
        # Test direct redaction method
        dirty_payload = {
            "api_key": dummy_key,
            "nested": {
                "auth_token": "secret_token_abc",
                "message": f"Calling API using key {dummy_key} for user"
            },
            "list_items": [f"Header: Bearer {dummy_key}"]
        }
        
        Tracker.record_event(
            run_id=redact_run,
            event_type="test_redaction_event",
            agent_source="RedactionTester",
            summary=f"Event summary with key {dummy_key}",
            payload=dirty_payload
        )
        
        events = Tracker.get_events_for_run(redact_run)
        self.assertTrue(len(events) >= 1)
        test_ev = next(e for e in events if e.get("run_id") == redact_run)
        
        # Ensure raw key never appears in payload or summary
        payload_str = json.dumps(test_ev["payload"])
        summary_str = test_ev["summary"]
        self.assertNotIn(dummy_key, payload_str)
        self.assertNotIn(dummy_key, summary_str)
        
        # Verify raw events.json file line also does not contain the dummy key
        with open(config.EVENTS_JSON, "r", encoding="utf-8") as f:
            for line in f:
                if redact_run in line:
                    self.assertNotIn(dummy_key, line)
                    self.assertIn("[REDACTED_API_KEY]", line)

    def test_invocations_requests_responses_payloads(self):
        """Verifies that invocations, requests, and responses for agents, skills, and models are recorded with payloads."""
        test_run_id = f"req_resp_{uuid.uuid4().hex[:8]}"
        orchestrator = PipelineOrchestrator(run_id=test_run_id)
        result = orchestrator.run(
            origin="Boston, USA",
            destination="Dublin, Ireland",
            days=2,
            budget=900.0,
            interests=["Pubs", "History"]
        )
        self.assertTrue(result["success"])

        events = Tracker.get_events_for_run(test_run_id)
        event_types = [e["event_type"] for e in events]

        # Model requests and responses
        self.assertIn("model_request", event_types)
        self.assertIn("model_response", event_types)

        # Agent requests and responses
        self.assertIn("agent_request", event_types)
        self.assertIn("agent_response", event_types)

        # Skill requests and responses
        self.assertIn("skill_request", event_types)
        self.assertIn("skill_response", event_types)

        # Tool requests and responses
        self.assertIn("tool_request", event_types)
        self.assertIn("tool_response", event_types)

        # Pipeline request and response
        self.assertIn("pipeline_request", event_types)
        self.assertIn("pipeline_response", event_types)

        # Verify actual payloads are populated
        model_req = next(e for e in events if e["event_type"] == "model_request")
        self.assertIn("prompt", model_req["payload"])
        self.assertIn("contents", model_req["payload"])
        self.assertIn("model", model_req["payload"])
        self.assertIn("generation_config", model_req["payload"])

        model_resp = next(e for e in events if e["event_type"] == "model_response")
        self.assertIn("response", model_resp["payload"])
        self.assertIn("candidates", model_resp["payload"])
        self.assertIn("usage_metadata", model_resp["payload"])
        self.assertIn("model_version", model_resp["payload"])

        agent_req = next(e for e in events if e["event_type"] == "agent_request" and e["agent_source"] == "FlightResearcher")
        self.assertIn("destination", agent_req["payload"])
        self.assertEqual(agent_req["payload"]["destination"], "Dublin, Ireland")

        agent_resp = next(e for e in events if e["event_type"] == "agent_response" and e["agent_source"] == "FlightResearcher")
        self.assertIn("flights", agent_resp["payload"])

    def test_export_service(self):
        """Verifies text and PDF generators."""
        state = create_initial_state("Vienna, Austria", 1200, 3, ["Classical Music"])
        state["current_itinerary"] = {
            "total_estimated_cost": 850.0,
            "selected_flight": {"carrier": "Austrian Air", "estimated_cost": 300.0},
            "selected_hotel": {"name": "Grand Hotel", "nightly_rate": 120.0, "neighborhood": "Old Town"},
            "cost_breakdown": {"flight": 300.0, "lodging": 360.0, "activities": 190.0},
            "schedule": [
                {
                    "day": 1,
                    "neighborhood_focus": "Innere Stadt",
                    "insider_tip": "Visit St. Stephen at morning light.",
                    "events": [
                        {"name": "Opera House Tour", "time_slot": "Morning", "category": "Culture", "estimated_cost": 20.0}
                    ]
                }
            ]
        }
        text_out = generate_text_itinerary(state)
        self.assertIn("VIENNA, AUSTRIA", text_out)
        self.assertIn("Opera House Tour", text_out)

        pdf_buf = generate_pdf_itinerary(state)
        self.assertGreater(pdf_buf.getbuffer().nbytes, 100)

    def test_flask_endpoints(self):
        """Verifies web application endpoints."""
        client = app.test_client()

        # Test Main Page
        res = client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"WanderAI", res.data)

        # Test History Endpoint
        res = client.get("/api/history")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("metrics", data)
        self.assertIn("itineraries", data)

        # Test Generate API
        res = client.post("/api/generate", json={
            "origin": "Seattle, USA",
            "destination": "Vancouver, Canada",
            "duration": 2,
            "budget": 800,
            "departure_date": "2026-11-20",
            "interests": "Coffee, Mountains"
        })
        self.assertEqual(res.status_code, 200)
        gen_data = res.get_json()
        self.assertTrue(gen_data["success"])
        run_id = gen_data["run_id"]

        # Verify departure_date in history
        res_hist = client.get("/api/history")
        hist_data = res_hist.get_json()
        run_record = next((r for r in hist_data["itineraries"] if r.get("run_id") == run_id), None)
        self.assertIsNotNone(run_record)
        self.assertEqual(run_record.get("travel_date"), "2026-11-20")

        # Test Events for Run
        res = client.get(f"/api/events/{run_id}")
        self.assertEqual(res.status_code, 200)
        ev_data = res.get_json()
        self.assertTrue(len(ev_data["events"]) > 0)

        # Test TXT and PDF Downloads
        res_txt = client.get(f"/download/txt/{run_id}")
        self.assertEqual(res_txt.status_code, 200)

        res_pdf = client.get(f"/download/pdf/{run_id}")
        self.assertEqual(res_pdf.status_code, 200)

    def test_detailed_day_by_day_schedule_requirements(self):
        """Verifies each day contains Day number, estimated_cost, Breakfast, Lunch, Dinner, and activities have location & duration."""
        orchestrator = PipelineOrchestrator(run_id="schedule_detail_test_run")
        result = orchestrator.run(
            origin="San Francisco, USA",
            destination="Lisbon, Portugal",
            days=2,
            budget=1600.0,
            interests=["Pastries", "Tram 28", "Fado"],
            departure_date="2026-10-01"
        )
        self.assertTrue(result["success"])
        itin = result["state"]["current_itinerary"]
        schedule = itin.get("schedule", [])
        self.assertEqual(len(schedule), 2)

        for day in schedule:
            # 1. Day number and estimated cost for that day
            self.assertIn("day", day)
            self.assertIn("estimated_cost", day)
            self.assertGreater(day["estimated_cost"], 0)

            # 2. Suggested dining for all meals: Breakfast, Lunch, Dinner
            categories = [e.get("category", "").lower() for e in day.get("events", [])]
            has_breakfast = any("breakfast" in c for c in categories)
            has_lunch = any("lunch" in c for c in categories)
            has_dinner = any("dinner" in c for c in categories)

            self.assertTrue(has_breakfast, f"Day {day['day']} missing Breakfast")
            self.assertTrue(has_lunch, f"Day {day['day']} missing Lunch")
            self.assertTrue(has_dinner, f"Day {day['day']} missing Dinner")

            # 3. For every activity: Time slot, Name, Estimated cost, Duration, Location
            for ev in day.get("events", []):
                self.assertIn("name", ev)
                self.assertTrue(bool(ev["name"]))
                self.assertIn("time_slot", ev)
                self.assertTrue(bool(ev["time_slot"]))
                self.assertIn("estimated_cost", ev)
                self.assertIsInstance(ev["estimated_cost"], (int, float))
                self.assertIn("location", ev)
                self.assertTrue(bool(ev["location"]))
                self.assertIn("duration_hours", ev)
                self.assertGreater(ev["duration_hours"], 0)

if __name__ == "__main__":
    unittest.main()
