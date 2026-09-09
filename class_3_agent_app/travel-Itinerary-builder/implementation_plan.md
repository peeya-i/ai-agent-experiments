# Implementation Plan - Travel Itinerary Builder

Build an autonomous, multi-agent AI pipeline and Flask web application for generating structured, multi-day vacation itineraries matching user constraints and budget.

## User Review Required

> [!IMPORTANT]
> **Key Architecture & Component Choices**:
> 1. **Framework**: `google.adk` with `SequentialAgent`, `ParallelAgent`, and `LoopAgent`.
> 2. **Model**: Configured via `GEMINI_MODEL` (defaulting to `gemini-2.0-flash` or `gemini-2.5-flash`) with API key from `GEMINI_API_KEY` loaded from `.env`.
> 3. **Frontend**: Flask application with interactive form validation, real-time generation tracking, and rich visual itinerary presentation (day-by-day timelines, budget breakdown charts/cards, and agent iteration logs).

## Proposed Architecture & File Structure

```
travel-Itinerary-builder/
├── app.py                      # Flask application entry point & API endpoints
├── config.py                   # Configuration, environment loading, Gemini settings
├── pipeline/
│   ├── __init__.py
│   ├── state.py                # Global state schema and state helper functions
│   ├── agents.py               # ParallelAgent (Discovery) and LoopAgent (Refinement) definitions
│   ├── tools.py                # Tools for research, scheduling, budget checks & loop exit
│   └── runner.py               # Orchestration runner to execute the sequential pipeline
├── templates/
│   └── index.html              # Modern, responsive UI with glassmorphism & rich itinerary display
├── static/
│   ├── css/
│   │   └── style.css           # Modern styling, animations, responsive layout
│   └── js/
│       └── app.js              # Client-side validation, AJAX API calls, and dynamic rendering
├── requirements.txt            # Project dependencies (flask, python-dotenv, google-adk, etc.)
└── .env.example                # Example environment variables template
```

## Detailed Component Plan

### 1. Global State & Schema (`pipeline/state.py`)
Implements the exact JSON schema required by `SPECIFICATIONS.md`:
```json
{
  "user_input": {
    "destination": "string",
    "budget": 0.0,
    "days": 0,
    "interests": []
  },
  "raw_research": {
    "flights": [],
    "hotels": [],
    "activities": []
  },
  "current_itinerary": {
    "total_estimated_cost": 0.0,
    "schedule": [
      {
        "day": 1,
        "events": []
      }
    ]
  },
  "critic_feedback": "",
  "budget_approved": false
}
```

### 2. Multi-Agent Pipeline (`pipeline/agents.py`, `pipeline/tools.py`)
- **Discovery Phase (`ParallelAgent`)**:
  - `FlightResearcher`: Discovers airline options, flight durations, and transport costs.
  - `HotelResearcher`: Discovers hotel/lodging options across budget tiers (luxury, mid-range, budget) matching interests and location.
  - `ActivityPlanner`: Gathers landmarks, dining, culture, outdoor activities, and tours tailored to user interests.
- **Optimization Phase (`LoopAgent`)** (max iterations = 5):
  - `Scheduler`: Synthesizes research into a day-by-day sequence. **Crucially reads `critic_feedback`** from previous iterations to downgrade hotels, swap paid tours for free alternatives, or reduce dining tiers when necessary.
  - `BudgetEnforcer`: Compares total estimated cost against user budget.
    - If `total_estimated_cost <= budget`: sets `budget_approved = True` and invokes `exit_loop`.
    - If `total_estimated_cost > budget`: sets `budget_approved = False`, provides specific actionable `critic_feedback` for the Scheduler, and continues the loop.
- **Graceful Failure Handling**: If budget is impossible after 5 iterations, outputs the best optimized plan with transparent budget difference warnings and cost-saving tips without crashing.

### 3. Flask Backend & Web Application (`app.py`, `templates/`, `static/`)
- Web Interface:
  - Form inputs: Destination, Budget ($), Duration (days), Interests (multi-tag selection & custom additions).
  - Client-side & Server-side validation for missing/invalid fields.
  - Asynchronous generation (`/api/generate`) with detailed progress steps.
  - Rich Itinerary Display:
    - Overview summary card (Total Cost vs Budget, Approval status, Iterations taken).
    - Day-by-Day timeline with event cards (time, activity, category, estimated cost).
    - Research options drawer (available flights, hotels, activities).
    - Budget breakdown summary.
    - Export / Print / Download JSON options.

## Verification Plan

### Automated & Unit Tests
- Test pipeline state initialization and validation.
- Test `ParallelAgent` and `LoopAgent` orchestration with mock / live inputs.
- Test budget reduction iteration: verify that `Scheduler` responds to `critic_feedback` and reduces total cost across iterations.
- Test edge cases: extremely low budget (graceful handling), invalid inputs (missing fields).

### Manual Verification
- Start Flask dev server and test:
  1. Standard request (e.g. Tokyo, 5 days, $2500, sushi, culture).
  2. Tight budget request (e.g. Paris, 4 days, $500) to verify loop refinement.
  3. Form validation triggers when required fields are missing.
