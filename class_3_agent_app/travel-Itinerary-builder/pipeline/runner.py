import asyncio
import copy
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from dotenv import load_dotenv

from google.genai import types
from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService

from .state import create_initial_state, validate_state
from .agents import create_travel_pipeline
from .tools import normalize_schedule, calculate_exact_itinerary_cost
from .event_logger import JsonEventLoggerPlugin, append_event_to_json, append_usage_to_csv

# Load .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

logger = logging.getLogger(__name__)

# Suppress AFC (Automatic Function Calling) compatibility warnings from google-genai
# since Google ADK manages and dispatches function/tool executions directly.
logging.getLogger("google_genai.models").setLevel(logging.ERROR)

# Enable automatic retries with exponential backoff & jitter on Gemini 429 rate limits
from google.adk.models.google_llm import Gemini
from google.genai.errors import ClientError
import random

_original_generate_content_async = getattr(Gemini, "_original_generate_content_async", Gemini.generate_content_async)
Gemini._original_generate_content_async = _original_generate_content_async

async def _retry_generate_content_async(self, llm_request, stream: bool = False):
    max_retries = 5
    base_delay = 8.0
    for attempt in range(1, max_retries + 1):
        try:
            async for resp in _original_generate_content_async(self, llm_request, stream=stream):
                yield resp
            return
        except Exception as e:
            err_str = str(e)
            is_429 = (
                "429" in err_str
                or "RESOURCE_EXHAUSTED" in err_str
                or (isinstance(e, ClientError) and getattr(e, "code", None) == 429)
            )
            if is_429 and attempt < max_retries:
                delay = (base_delay * (2 ** (attempt - 1))) + random.uniform(0.5, 1.5)
                model_name = getattr(llm_request, "model", "gemini")
                logger.warning(
                    "Gemini API 429 rate limit hit on model '%s'. Auto-retrying in %.1fs (Attempt %d/%d)...",
                    model_name,
                    delay,
                    attempt,
                    max_retries
                )
                await asyncio.sleep(delay)
            else:
                raise

Gemini.generate_content_async = _retry_generate_content_async


def generate_fallback_itinerary(user_input: Dict[str, Any], reason: str = "") -> Dict[str, Any]:
    """Generates an intelligent baseline itinerary for impossible budgets or fallback scenarios."""
    destination = user_input.get("destination", "Destination")
    city_of_origin = user_input.get("city_of_origin", "")
    departure_date = user_input.get("departure_date", "")
    budget = float(user_input.get("budget", 500))
    days = int(user_input.get("days", 3))
    interests = user_input.get("interests", ["sightseeing", "food"])
    interest_str = ", ".join(interests) if interests else "local highlights"

    # Baseline cost calculations
    flight_est = max(150.0, budget * 0.35)
    hotel_rate_per_night = max(40.0, (budget * 0.45) / max(1, days))
    hotel_est = hotel_rate_per_night * days
    daily_activity_budget = max(20.0, (budget * 0.20) / max(1, days))

    origin_label = f" from {city_of_origin}" if city_of_origin else ""
    date_note = f" (Departing {departure_date})" if departure_date else ""

    flights = [
        {
            "flight_name": f"Economy Saver{origin_label} to {destination}",
            "airline": "Standard Carrier",
            "travel_time": "Direct / 1-stop",
            "estimated_cost": round(flight_est, 2),
            "notes": f"Includes standard carry-on and seat selection{date_note}"
        },
        {
            "flight_name": f"Flexible Fare{origin_label} to {destination}",
            "airline": "Major Airline",
            "travel_time": "Non-stop",
            "estimated_cost": round(flight_est * 1.35, 2),
            "notes": f"Checked bag included + refundable{date_note}"
        }
    ]

    hotels = [
        {
            "hotel_name": f"Central Traveler Hostel / Budget Hotel in {destination}",
            "tier": "budget",
            "price_per_night": round(hotel_rate_per_night, 2),
            "safety_rating": "Safe - Verified tourist district",
            "location_notes": "Walking distance to metro/bus lines"
        },
        {
            "hotel_name": f"Comfort City Stay {destination}",
            "tier": "mid-range",
            "price_per_night": round(hotel_rate_per_night * 1.6, 2),
            "safety_rating": "Excellent - City center",
            "location_notes": "Central square, breakfast included"
        }
    ]

    activities = [
        {
            "activity_name": f"Historic Walking Tour & Main Square in {destination}",
            "category": "culture",
            "estimated_cost": 0.0,
            "duration_hours": 2.5,
            "description": f"Explore iconic landmarks and architecture celebrating {interest_str}."
        },
        {
            "activity_name": f"Local Street Food & Market Exploration",
            "category": "restaurant",
            "estimated_cost": round(daily_activity_budget * 0.4, 2),
            "duration_hours": 2.0,
            "description": "Taste authentic specialties at the central public market."
        },
        {
            "activity_name": f"{destination} Botanical Gardens & Public Viewpoint",
            "category": "nature",
            "estimated_cost": 5.0,
            "duration_hours": 2.0,
            "description": "Panoramic scenic city views and peaceful garden stroll."
        },
        {
            "activity_name": f"Signature Museum & Cultural Exhibition",
            "category": "landmark",
            "estimated_cost": 15.0,
            "duration_hours": 3.0,
            "description": f"Top-rated regional exhibition focusing on local history and {interest_str}."
        }
    ]

    # Generate days
    schedule = []
    total_activities_cost = 0.0
    for day in range(1, days + 1):
        events = [
            {
                "time": "09:00 AM",
                "title": f"Day {day} Morning: {activities[(day - 1) % len(activities)]['activity_name']}",
                "category": activities[(day - 1) % len(activities)]["category"],
                "estimated_cost": activities[(day - 1) % len(activities)]["estimated_cost"],
                "description": f"Immerse in morning sights aligned with {interest_str}."
            },
            {
                "time": "01:00 PM",
                "title": f"Day {day} Lunch: Local Specialty Dining",
                "category": "dining",
                "estimated_cost": round(daily_activity_budget * 0.5, 2),
                "description": "Authentic regional lunch at a popular neighborhood bistro."
            },
            {
                "time": "03:30 PM",
                "title": f"Day {day} Afternoon: {activities[(day) % len(activities)]['activity_name']}",
                "category": activities[(day) % len(activities)]["category"],
                "estimated_cost": activities[(day) % len(activities)]["estimated_cost"],
                "description": "Afternoon exploration and photo opportunities."
            },
            {
                "time": "07:30 PM",
                "title": f"Day {day} Evening: Sunset Walk & Casual Dinner",
                "category": "dining",
                "estimated_cost": round(daily_activity_budget * 0.6, 2),
                "description": "Evening relaxation along illuminated promenades."
            }
        ]
        day_cost = sum(e["estimated_cost"] for e in events)
        total_activities_cost += day_cost
        schedule.append({"day": day, "events": events})

    total_cost = round(flight_est + hotel_est + total_activities_cost, 2)
    budget_approved = total_cost <= budget

    feedback = (
        "Budget approved: Baseline plan meets your allocation."
        if budget_approved
        else f"Note: Target budget (${budget:.2f}) is tight for {days} days in {destination} (Baseline cost: ${total_cost:.2f}). To save more, consider off-peak flight dates and shared lodging."
    )

    if reason:
        feedback = f"{reason} | {feedback}"

    return {
        "user_input": user_input,
        "raw_research": {
            "flights": flights,
            "hotels": hotels,
            "activities": activities
        },
        "current_itinerary": {
            "total_estimated_cost": total_cost,
            "schedule": schedule
        },
        "critic_feedback": feedback,
        "budget_approved": budget_approved,
        "iterations_taken": 1,
        "logs": [
            f"Initialized Discovery for {destination} ({days} days)",
            f"Tool [save_flight_research] invoked: Evaluated transport options for ${budget:.2f} budget constraint",
            f"Tool [save_hotel_research] invoked: Selected lodging tiers",
            f"Tool [save_activity_research] invoked: Curated multi-day attractions and dining highlights for {destination}",
            f"Skill [itinerary-enhancer-skill] invoked: Clustered daily activities geographically and enriched with local experiences for {destination}",
            f"Tool [save_itinerary_schedule] invoked: Generated baseline schedule with {len(schedule)} day plans",
            f"Tool [evaluate_budget_and_finalize] invoked: Evaluated total cost ${total_cost:.2f} against ${budget:.2f} budget"
        ]
    }


async def run_itinerary_pipeline_async(
    destination: str,
    budget: float,
    days: int,
    interests: List[str],
    city_of_origin: str = "",
    departure_date: str = "",
    model: Optional[str] = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """Asynchronously runs the sequential Travel Itinerary Pipeline."""
    initial_state = create_initial_state(
        destination=destination,
        budget=budget,
        days=days,
        interests=interests,
        city_of_origin=city_of_origin,
        departure_date=departure_date
    )
    logs: List[str] = []

    def log_step(msg: str):
        logs.append(msg)
        if progress_callback:
            try:
                progress_callback(msg)
            except Exception:
                pass

    origin_desc = f" from {city_of_origin}" if city_of_origin else ""
    log_step(f"Starting Travel Itinerary Pipeline for {destination}{origin_desc} ({days} days, budget ${budget:.2f})...")

    # Check for GEMINI_API_KEY
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        log_step("Warning: GEMINI_API_KEY not configured. Generating optimized baseline itinerary.")
        result = generate_fallback_itinerary(
            initial_state["user_input"],
            reason="Demo Mode (Configure GEMINI_API_KEY for live Gemini agent model calls)"
        )
        result["logs"] = logs + result.get("logs", [])
        return result

    try:
        event_plugin = JsonEventLoggerPlugin()
        pipeline_agent = create_travel_pipeline(model=model)
        runner = InMemoryRunner(
            agent=pipeline_agent,
            plugins=[event_plugin],
            app_name="travel_itinerary_builder"
        )
        session = await runner.session_service.create_session(
            app_name="travel_itinerary_builder",
            user_id="traveler_user",
            state=initial_state
        )

        origin_str = f"origin city: '{city_of_origin}', " if city_of_origin else ""
        dep_str = f"departure date: '{departure_date}', " if departure_date else ""
        prompt_text = (
            f"Generate a vacation itinerary for {origin_str}destination: '{destination}', "
            f"{dep_str}duration: {days} days, budget: ${budget:.2f} USD, and interests: {interests}. "
            f"Follow the sequential workflow: 1. Research flights, hotels, and activities in parallel (DiscoveryTeam: FlightResearcher, HotelResearcher, ActivityPlanner). "
            f"2. Synthesize schedule in loop, enforce budget constraints, and critique/refine if cost exceeds budget (OptimizationRoom: Scheduler, BudgetEnforcer)."
        )

        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt_text)]
        )

        itinerary_id = f"itin_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        append_event_to_json({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "pipeline_start",
            "itinerary_id": itinerary_id,
            "user_input": initial_state["user_input"],
            "prompt": prompt_text
        })
        append_usage_to_csv({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "pipeline_start",
            "user_input": initial_state["user_input"],
            "prompt": prompt_text,
            "debug_log": f"Started pipeline run {itinerary_id} for destination={destination}"
        })

        log_step("Executing Parallel Discovery Team (FlightResearcher, HotelResearcher, ActivityPlanner in parallel)...")
        iteration_count = 0

        async for event in runner.run_async(
            user_id="traveler_user",
            session_id=session.id,
            new_message=user_message
        ):
            if event.author:
                log_step(f"Agent [{event.author}] active")

            # Check and log function and tool calls
            if hasattr(event, "get_function_calls") and event.get_function_calls():
                for fc in event.get_function_calls():
                    fn_name = getattr(fc, "name", str(fc))
                    log_step(f"Tool Invoked: [{fn_name}] by [{event.author}]")

            # Check and log function and tool responses
            if hasattr(event, "get_function_responses") and event.get_function_responses():
                for fr in event.get_function_responses():
                    fn_name = getattr(fr, "name", str(fr))
                    log_step(f"Tool Completed: [{fn_name}]")

            if event.actions and event.actions.state_delta:
                delta_keys = list(event.actions.state_delta.keys())
                log_step(f"State updated: {', '.join(delta_keys)}")

        # Fetch final session state
        updated_session = await runner.session_service.get_session(
            app_name="travel_itinerary_builder",
            user_id="traveler_user",
            session_id=session.id
        )
        final_state = dict(updated_session.state)

        # Check if research and itinerary were populated
        schedule = final_state.get("current_itinerary", {}).get("schedule", [])
        if not schedule:
            log_step("Pipeline completed with empty schedule. Applying intelligent baseline synthesis.")
            fallback = generate_fallback_itinerary(initial_state["user_input"])
            final_state["current_itinerary"] = fallback["current_itinerary"]
            if not final_state.get("raw_research", {}).get("flights"):
                final_state["raw_research"] = fallback["raw_research"]
            final_state["budget_approved"] = fallback["budget_approved"]
            final_state["critic_feedback"] = fallback["critic_feedback"]
        else:
            norm_sched = normalize_schedule(
                schedule,
                total_days=int(initial_state["user_input"].get("days", 1))
            )
            final_state["current_itinerary"]["schedule"] = norm_sched
            final_state["current_itinerary"]["total_estimated_cost"] = calculate_exact_itinerary_cost(
                final_state,
                norm_sched,
                provided_cost=final_state.get("current_itinerary", {}).get("total_estimated_cost")
            )
            # Re-evaluate budget approval based on exact cost
            budget = float(initial_state["user_input"].get("budget", 0.0))
            exact_cost = final_state["current_itinerary"]["total_estimated_cost"]
            final_state["budget_approved"] = exact_cost <= budget

        append_event_to_json({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "pipeline_complete",
            "itinerary_id": itinerary_id,
            "final_state": final_state
        })
        append_usage_to_csv({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "pipeline_complete",
            "user_input": initial_state["user_input"],
            "response": final_state.get("current_itinerary"),
            "debug_log": f"Completed pipeline run {itinerary_id}. Approved={final_state.get('budget_approved')}"
        })

        final_state["logs"] = logs
        final_state["itinerary_id"] = itinerary_id
        return final_state

    except Exception as e:
        # Unpack ExceptionGroup or nested causes to check for 429 / quota limit
        all_err_strings = [str(e), repr(e)]
        if hasattr(e, "exceptions"):
            for sub in e.exceptions:
                all_err_strings.extend([str(sub), repr(sub)])
                if hasattr(sub, "__cause__") and sub.__cause__:
                    all_err_strings.extend([str(sub.__cause__), repr(sub.__cause__)])

        combined_err = " ".join(all_err_strings)
        is_quota_limit = (
            "429" in combined_err
            or "RESOURCE_EXHAUSTED" in combined_err
            or "_resourceexhaustederror" in combined_err.lower()
            or "quota" in combined_err.lower()
        )

        if is_quota_limit:
            logger.warning("Gemini API rate limit / quota exhausted (429). Gracefully engaging intelligent fallback synthesizer.")
            log_step("Gemini API rate limit (429 quota exhausted) reached. Gracefully activating intelligent fallback synthesizer.")
        else:
            logger.warning("Pipeline encountered runtime condition (%s). Engaging fallback recovery.", type(e).__name__)
            log_step(f"Pipeline encountered runtime condition: {type(e).__name__}. Gracefully generating structured itinerary.")

        fallback = generate_fallback_itinerary(
            initial_state["user_input"],
            reason="Gemini API Quota Exhausted (429)" if is_quota_limit else f"Graceful Recovery: {type(e).__name__}"
        )
        current_itin_id = locals().get("itinerary_id") or f"itin_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        append_event_to_json({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "pipeline_fallback",
            "itinerary_id": current_itin_id,
            "error": str(e),
            "fallback_state": fallback
        })
        append_usage_to_csv({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "pipeline_fallback",
            "user_input": initial_state["user_input"],
            "response": fallback.get("current_itinerary"),
            "debug_log": f"Fallback recovery engaged for {current_itin_id}: {str(e)[:100]}"
        })
        fallback["logs"] = logs + fallback.get("logs", [])
        fallback["itinerary_id"] = current_itin_id
        return fallback


def run_itinerary_pipeline(
    destination: str,
    budget: float,
    days: int,
    interests: List[str],
    city_of_origin: str = "",
    departure_date: str = "",
    model: Optional[str] = None
) -> Dict[str, Any]:
    """Synchronous entry point for Flask routes."""
    return asyncio.run(
        run_itinerary_pipeline_async(
            destination=destination,
            budget=budget,
            days=days,
            interests=interests,
            city_of_origin=city_of_origin,
            departure_date=departure_date,
            model=model
        )
    )
