# Travel Itinerary Builder

WanderAI is an autonomous, multi-agent AI pipeline and web application that generates structured, multi-day vacation itineraries matching traveler interests, geographical clustering, and strict budget boundaries.

---

## 🏗️ Architecture & How It Works

The system implements a **Sequential Pipeline** coordinating a **Parallel Discovery Phase** followed by an iterative **Loop Refinement Phase**:

```
+-------------------------------------------------------------------------+
|                           User Input & Options                          |
|    (Origin, Destination, Duration, Budget, Departure Date, Interests)    |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  Phase 1: ParallelAgent (Discovery Team)                |
|  - FlightResearcher : Locates transport, travel times, and costs       |
|  - HotelResearcher  : Finds lodging matching interests & safety         |
|  - ActivityPlanner  : Compiles landmarks, dining, and tours            |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  Phase 2: LoopAgent (Optimization Room)                 |
|  - Scheduler        : Groups activities geographically by day to        |
|                       minimize transit, invokes Gemini skills           |
|                       (LocalVibeSkill, HiddenGemSkill), and applies     |
|                       critic feedback across iterations                 |
|  - BudgetEnforcer   : Compares total cost vs target budget.             |
|                       - Cost <= Budget -> Approves & terminates loop    |
|                       - Cost > Budget  -> Issues critic feedback and   |
|                                           triggers next iteration       |
|  - Cap              : Up to 3 iterations with graceful failure handling |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                           Artifacts Logging                             |
|  - artifacts/usages.csv : Request summary, costs, status, event count   |
|  - artifacts/events.json: Single-line log per record of invocations,    |
|                           requests, and responses of agents, skills,    |
|                           tools, and models with full payloads          |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                      Web UI & Export (Flask App)                        |
|  - Day-by-day cluster timeline with insider tips & hidden gems          |
|  - Text (.txt) and PDF (.pdf) downloads                                 |
|  - Itineraries history modal & event logs table with clipboard copy     |
+-------------------------------------------------------------------------+
```

### 1. Parallel Discovery Phase (`ParallelAgent`)
- Runs concurrently using a `ThreadPoolExecutor`.
- `FlightResearcher`: Locates transit options, route types (Direct vs 1-Stop), travel duration, and round-trip pricing.
- `HotelResearcher`: Finds accommodations tailored to user interests, neighborhood safety ratings, and nightly pricing.
- `ActivityPlanner`: Gathers attractions and dining grouped by local neighborhoods.

### 2. Iterative Refinement Phase (`LoopAgent`)
- `Scheduler`:
  - Utilizes `GeoClusteringTool` to group activities and dining by neighborhood, eliminating back-and-forth transit time.
  - Formats each day in a clearly separated, day-by-day structure with:
    - Day number and neighborhood focus.
    - **Estimated cost for each day** (`estimated_cost`).
    - **Suggested dining for all meals**: Breakfast (`🍳`), Lunch (`🥗`), and Dinner (`🍽️`).
    - **Activity Details**: Time slot, Name of activity, Estimated cost, Duration (`⏱️`), Location (`📍`), and Description.
  - Implements **Gemini Skills**:
    - `LocalVibeSkill`: Injects authentic insider tips and cultural customs for each day's neighborhood focus.
    - `HiddenGemSkill`: Recommends unexpected, charming off-the-beaten-path mini stops.
  - Reads `critic_feedback` from prior iterations to downgrade lodging tiers, select budget transit, and substitute free walking sights.
- `BudgetEnforcer`:
  - Utilizes `BudgetCalculatorTool` to compute total trip costs (transit + lodging + activities + dining).
  - Sets `budget_approved = True` if cost is within budget.
  - Otherwise generates detailed `critic_feedback` and triggers the next iteration (up to 3 loops).
- **Graceful Failure Handling**: If an impossible budget is provided (e.g., $10 for 5 days in Tokyo), the agent selects the lowest possible budget options and issues a clear budget warning banner without crashing.

### 3. Tools Layer (`pipeline/tools.py`)
- `GeoClusteringTool`: Organizes activities by geographic proximity and builds a structured day schedule (Breakfast $\rightarrow$ Morning Sight $\rightarrow$ Lunch $\rightarrow$ Afternoon Exploration $\rightarrow$ Dinner).
- `BudgetCalculatorTool`: Computes accurate cost breakdowns across lodging, transit, and daily dining/activities.

### 4. Global State Schema
All agents interact with a single, centralized dictionary state:
```json
{
  "user_input": {
    "origin": "string",
    "destination": "string",
    "budget": 0.0,
    "days": 0,
    "departure_date": "string",
    "interests": ["string"]
  },
  "raw_research": {
    "flights": [],
    "hotels": [],
    "activities": []
  },
  "current_itinerary": {
    "total_estimated_cost": 0.0,
    "cost_breakdown": {
      "flight": 0.0,
      "lodging": 0.0,
      "activities": 0.0
    },
    "selected_flight": {},
    "selected_hotel": {},
    "schedule": [
      {
        "day": 1,
        "estimated_cost": 0.0,
        "neighborhood_focus": "string",
        "insider_tip": "string",
        "events": [
          {
            "name": "string",
            "time_slot": "string",
            "category": "Breakfast | Lunch | Dinner | Sight | Hidden Gem",
            "location": "string",
            "duration_hours": 1.0,
            "estimated_cost": 0.0,
            "description": "string"
          }
        ]
      }
    ]
  },
  "critic_feedback": "string",
  "budget_approved": false
}
```

---

## 💻 Web Application Features

The Flask application features a dual-tab dashboard:

1. **Tab 1: Itinerary Builder & Generator**:
   - Form inputs for origin, destination, duration, budget, departure date, and interests.
   - Interactive pipeline execution stepper.
   - Financial breakdown strip (Transit, Lodging, Activities, Total Cost vs Target Budget).
   - Day-by-day cards featuring neighborhood focus tags, day cost badges, all 3 daily meals, and activity details.
   - **Download Buttons**: Export itinerary as plain text (`.txt`) or styled PDF (`.pdf`).

2. **Tab 2: Itineraries & Event Logs**:
   - **Metric Cards**: *Itineraries Requested*, *Itineraries Generated*, *Failed Requests*, and *Events Logged*.
   - **Itineraries Requested Table**: Displays all historical runs from `artifacts/usages.csv` with travel dates, origin, budget, cost, and status.
   - **Full Itinerary Popup**: Clicking any row displays the full itinerary in a modal dialog matching the Page 1 layout.
   - **Lifecycle Event Logs Table**: Granular agent, skill, tool, and model lifecycle events recorded on a per-run basis.
   - **Event Payload Popup**: Clicking "Payload" displays complete event details in formatted JSON with a **"Copy to Clipboard"** button.
   - **API Key Redaction**: Sensitive API keys and auth tokens are automatically redacted prior to storage in `artifacts/events.json`.

---

## 🚀 How to Run the App

### 1. Prerequisites
- Python 3.10+
- Virtual environment

### 2. Activate Virtual Environment & Install Dependencies
```bash
source .venv/bin/activate
pip install -r requirements.txt
```
*(Or use `.venv/bin/python app.py` directly)*

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Configure the following variables in `.env`:
```ini
# Gemini API Key (If omitted, the app runs in resilient simulation mode)
GEMINI_API_KEY=your_gemini_api_key_here

# Primary Gemini Model
GEMINI_MODEL=gemini-2.5-flash

# Fallback Gemini Model (Used automatically if primary model is unavailable)
GEMINI_FALLBACK_MODEL=gemini-1.5-flash

# Server Port and Debug
PORT=5001
FLASK_DEBUG=True
```

### 4. Start the Application
```bash
python app.py
```

Open your browser and navigate to:
```
http://localhost:5001
```

---

## 🧪 Running Automated Tests

Run the full automated test suite verifying state schema, parallel discovery, loop optimization, budget boundaries, graceful error handling, export service, and API endpoints:

```bash
python -m unittest tests/test_pipeline.py
```

---

## 📂 Project Structure

```
.
├── app.py                     # Flask web app and API routing
├── config.py                  # Configuration loader & artifact paths
├── requirements.txt           # Python dependencies
├── .env.example               # Template environment configuration
├── SPECIFICATIONS.md          # Project specification document
├── README.md                  # Application guide & documentation
├── pipeline/
│   ├── state.py               # Centralized Global State definition
│   ├── gemini_service.py      # Resilient Gemini client with primary/fallback
│   ├── parallel_agent.py      # FlightResearcher, HotelResearcher, ActivityPlanner
│   ├── skills.py              # LocalVibeSkill and HiddenGemSkill
│   ├── tools.py               # GeoClusteringTool and BudgetCalculatorTool
│   ├── loop_agent.py          # Scheduler, BudgetEnforcer, and LoopAgent
│   └── orchestrator.py        # Sequential Pipeline orchestrator
├── services/
│   ├── tracker.py             # usages.csv and events.json logging service
│   └── export_service.py      # Plain text & PDF export generators
├── static/
│   ├── css/
│   │   └── style.css          # Modern dark-mode styling & glassmorphism
│   └── js/
│       └── app.js             # Interactive UI, tab switching & clipboard copy
├── templates/
│   └── index.html             # Main dual-tab web interface
├── artifacts/
│   ├── usages.csv             # Run summary records
│   ├── events.json            # Granular lifecycle interaction event logs
│   └── runs/                  # Saved run itineraries in JSON
└── tests/
    └── test_pipeline.py       # Comprehensive unit test suite
```
