import json
import tempfile
import unittest
from pathlib import Path
from app import app
from pipeline.event_logger import (
    append_event_to_json,
    get_all_itineraries_with_events,
    get_itinerary_by_id,
    summarize_event_for_display
)


class TestItineraryHistoryAndLogs(unittest.TestCase):
    """Test suite for itinerary extraction and event logging endpoints."""

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        self.temp_dir = tempfile.TemporaryDirectory()
        self.events_file = Path(self.temp_dir.name) / "test_events.json"

        # Populate sample events for 2 itineraries
        # Itinerary 1
        append_event_to_json({
            "timestamp": "2026-08-30T10:00:00Z",
            "event_type": "pipeline_start",
            "itinerary_id": "test_itin_1",
            "user_input": {
                "destination": "Kyoto, Japan",
                "city_of_origin": "San Francisco",
                "budget": 2500.0,
                "days": 5,
                "interests": ["Historic Culture", "Food & Dining"]
            },
            "prompt": "Test prompt for Kyoto"
        }, self.events_file)

        append_event_to_json({
            "timestamp": "2026-08-30T10:00:02Z",
            "event_type": "model_request",
            "agent": "FlightResearcher",
            "model": "gemini-3.5-flash-lite",
            "request_contents": [{"text": "Research flights to Kyoto"}]
        }, self.events_file)

        append_event_to_json({
            "timestamp": "2026-08-30T10:00:04Z",
            "event_type": "tool_response",
            "agent": "FlightResearcher",
            "tool_name": "save_flight_research",
            "tool_result": "Successfully saved flights"
        }, self.events_file)

        append_event_to_json({
            "timestamp": "2026-08-30T10:00:10Z",
            "event_type": "pipeline_complete",
            "itinerary_id": "test_itin_1",
            "final_state": {
                "user_input": {"destination": "Kyoto, Japan", "budget": 2500.0, "days": 5},
                "current_itinerary": {
                    "total_estimated_cost": 2150.0,
                    "schedule": [{"day": 1, "events": []}]
                },
                "budget_approved": True,
                "logs": ["Discovery completed", "Budget approved"]
            }
        }, self.events_file)

        # Itinerary 2
        append_event_to_json({
            "timestamp": "2026-08-30T11:00:00Z",
            "event_type": "pipeline_start",
            "itinerary_id": "test_itin_2",
            "user_input": {
                "destination": "Paris, France",
                "budget": 1000.0,
                "days": 4,
                "interests": ["Museums & Art"]
            },
            "prompt": "Test prompt for Paris"
        }, self.events_file)

        append_event_to_json({
            "timestamp": "2026-08-30T11:00:05Z",
            "event_type": "pipeline_complete",
            "itinerary_id": "test_itin_2",
            "final_state": {
                "user_input": {"destination": "Paris, France", "budget": 1000.0, "days": 4},
                "current_itinerary": {
                    "total_estimated_cost": 1450.0,
                    "schedule": [{"day": 1, "events": []}]
                },
                "budget_approved": False,
                "logs": ["Discovery completed", "Over budget"]
            }
        }, self.events_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_get_all_itineraries_with_events(self):
        """Verify grouping of events into itineraries."""
        itineraries = get_all_itineraries_with_events(self.events_file)
        self.assertEqual(len(itineraries), 2)

        # Most recent first
        newest = itineraries[0]
        self.assertEqual(newest["destination"], "Paris, France")
        self.assertEqual(newest["budget"], 1000.0)
        self.assertEqual(newest["total_estimated_cost"], 1450.0)
        self.assertFalse(newest["budget_approved"])
        self.assertEqual(len(newest["events"]), 2)

        older = itineraries[1]
        self.assertEqual(older["destination"], "Kyoto, Japan")
        self.assertEqual(older["origin"], "San Francisco")
        self.assertEqual(older["total_estimated_cost"], 2150.0)
        self.assertTrue(older["budget_approved"])
        self.assertEqual(len(older["events"]), 4)

    def test_get_itinerary_by_id(self):
        """Verify fetching single itinerary by ID."""
        itin = get_itinerary_by_id("test_itin_1", self.events_file)
        self.assertIsNotNone(itin)
        self.assertEqual(itin["destination"], "Kyoto, Japan")
        self.assertEqual(len(itin["events"]), 4)
        self.assertTrue(any(e["event_type"] == "model_request" for e in itin["events"]))

    def test_summarize_event_for_display(self):
        """Verify human-friendly summary generation."""
        ev = {
            "timestamp": "2026-08-30T10:00:00Z",
            "event_type": "pipeline_start",
            "user_input": {"destination": "Rome", "budget": 1500, "days": 3}
        }
        summarized = summarize_event_for_display(ev)
        self.assertIn("Rome", summarized["summary"])
        self.assertEqual(summarized["agent"], "System")

    def test_api_list_itineraries_endpoint(self):
        """Verify GET /api/itineraries endpoint."""
        response = self.app.get("/api/itineraries")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIsInstance(data["data"], list)
        self.assertGreaterEqual(data["count"], 0)

    def test_api_health_endpoint(self):
        """Verify health check returns healthy status."""
        response = self.app.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "healthy")


if __name__ == "__main__":
    unittest.main()
