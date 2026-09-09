"""Flask Application for Travel Itinerary Builder."""

import logging
import os
from typing import Any, Dict, List
from flask import Flask, jsonify, render_template, request

from config import DEBUG, GEMINI_API_KEY, GEMINI_MODEL, PORT
from pipeline.runner import run_itinerary_pipeline_async
from pipeline.state import validate_state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("travel_app")

# Suppress AFC (Automatic Function Calling) compatibility warnings from google-genai
# since Google ADK manages and dispatches function/tool executions directly.
logging.getLogger("google_genai.models").setLevel(logging.ERROR)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "travel-itinerary-builder-secret-2026")


@app.route("/")
def index():
    """Renders the main Travel Itinerary Builder UI."""
    return render_template(
        "index.html",
        gemini_model=GEMINI_MODEL,
        has_api_key=bool(GEMINI_API_KEY)
    )


@app.route("/api/generate", methods=["POST"])
async def generate_itinerary():
    """Generates an itinerary using the multi-agent pipeline."""
    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        data = {}

    destination = str(data.get("destination", "")).strip()
    city_of_origin = str(data.get("city_of_origin") or data.get("origin") or "").strip()
    departure_date = str(data.get("departure_date") or "").strip()
    raw_budget = data.get("budget", None)
    raw_days = data.get("days") or data.get("duration", None)
    raw_interests = data.get("interests", [])

    # Validate inputs as required by SPECIFICATIONS.md:
    # "The app will ask for the destination, budget, departure date, duration, and interests. If the information is missing, it will prompt the user to provide it."
    missing_fields = []
    if not destination:
        missing_fields.append("Destination")
    if raw_budget is None or raw_budget == "":
        missing_fields.append("Budget ($)")
    if raw_days is None or raw_days == "":
        missing_fields.append("Duration (days)")

    if missing_fields:
        return jsonify({
            "success": False,
            "error": f"Please provide the required missing information: {', '.join(missing_fields)}.",
            "missing_fields": missing_fields
        }), 400

    try:
        budget = float(raw_budget)
        if budget <= 0:
            return jsonify({
                "success": False,
                "error": "Budget must be a positive number greater than 0."
            }), 400
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "Invalid budget format. Please enter a valid number (e.g. 1500)."
        }), 400

    try:
        days = int(raw_days)
        if days <= 0 or days > 30:
            return jsonify({
                "success": False,
                "error": "Duration must be between 1 and 30 days."
            }), 400
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "Invalid duration format. Please enter an integer number of days (e.g. 5)."
        }), 400

    # Clean interests list
    if isinstance(raw_interests, str):
        interests = [i.strip() for i in raw_interests.split(",") if i.strip()]
    elif isinstance(raw_interests, list):
        interests = [str(i).strip() for i in raw_interests if str(i).strip()]
    else:
        interests = []

    if not interests:
        interests = ["Sightseeing", "Local Food", "Culture"]

    logger.info(
        "Received itinerary request: Origin='%s', Destination='%s', Date='%s', Budget=$%.2f, Days=%d, Interests=%s",
        city_of_origin, destination, departure_date, budget, days, interests
    )

    # Execute the multi-agent pipeline
    try:
        result_state = await run_itinerary_pipeline_async(
            destination=destination,
            budget=budget,
            days=days,
            interests=interests,
            city_of_origin=city_of_origin,
            departure_date=departure_date,
            model=GEMINI_MODEL
        )

        return jsonify({
            "success": True,
            "data": result_state,
            "is_valid_schema": validate_state(result_state)
        }), 200

    except Exception as e:
        logger.exception("Pipeline execution failed: %s", e)
        return jsonify({
            "success": False,
            "error": f"An unexpected error occurred during itinerary generation: {str(e)}"
        }), 500


@app.route("/api/itineraries", methods=["GET"])
def list_itineraries():
    """Returns a list of all created itineraries and their event summaries."""
    try:
        from pipeline.event_logger import get_all_itineraries_with_events
        itineraries = get_all_itineraries_with_events()
        return jsonify({
            "success": True,
            "count": len(itineraries),
            "data": itineraries
        }), 200
    except Exception as e:
        logger.exception("Failed to retrieve itineraries: %s", e)
        return jsonify({
            "success": False,
            "error": f"Failed to retrieve itineraries: {str(e)}"
        }), 500


@app.route("/api/itineraries/<itinerary_id>", methods=["GET"])
def get_itinerary_details(itinerary_id: str):
    """Returns the events and logs for a specific itinerary by ID."""
    try:
        from pipeline.event_logger import get_itinerary_by_id
        itinerary = get_itinerary_by_id(itinerary_id)
        if not itinerary:
            return jsonify({
                "success": False,
                "error": f"Itinerary '{itinerary_id}' not found."
            }), 404

        return jsonify({
            "success": True,
            "data": itinerary
        }), 200
    except Exception as e:
        logger.exception("Failed to retrieve itinerary %s: %s", itinerary_id, e)
        return jsonify({
            "success": False,
            "error": f"Failed to retrieve itinerary: {str(e)}"
        }), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "gemini_model": GEMINI_MODEL,
        "has_api_key": bool(GEMINI_API_KEY)
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
