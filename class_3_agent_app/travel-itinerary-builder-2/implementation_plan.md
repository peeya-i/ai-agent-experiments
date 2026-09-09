# Travel Itinerary Builder - Implementation Plan

Build a multi-agent AI pipeline and Flask web application that generates structured, multi-day vacation itineraries matching user interests, geographical clustering, and strict budget boundaries, with comprehensive execution logging, dual-tab dashboard, and export features.

## Architecture & System Design

```mermaid
flowchart TD
    UI[User Input Form & Options] --> Flask[Flask Web App]
    Flask --> Pipeline[Sequential Pipeline]
    
    subgraph Discovery [Parallel Discovery Phase (ParallelAgent)]
        direction TB
        FRes[FlightResearcher Agent]
        HRes[HotelResearcher Agent]
        ActP[ActivityPlanner Agent]
    end
    
    Pipeline --> Discovery
    Discovery --> State[(Global State)]
    
    subgraph Refinement [Loop Refinement Phase (LoopAgent - max 3 iter)]
        direction TB
        Sched[Scheduler Agent + Gemini Skills]
        Enf[BudgetEnforcer Agent]
        Crit[Critic Feedback Generator]
        Sched --> Enf
        Enf -- "cost > budget & iter < 3" --> Crit --> Sched
    end
    
    State --> Refinement
    Refinement --> Result[Final Itinerary & Status]
    
    Pipeline --> Logger[Artifacts Logger]
    Logger --> Usages[(artifacts/usages.csv)]
    Logger --> Events[(artifacts/events.json)]
```

### Core Architecture Components

1. **Agent Framework (`pipeline/` & `agents/`)**:
   - `GlobalState`: Dict wrapper matching specification schema (`user_input`, `raw_research`, `current_itinerary`, `critic_feedback`, `budget_approved`).
   - `ParallelAgent`: ThreadPool-based concurrent runner executing `FlightResearcher`, `HotelResearcher`, and `ActivityPlanner`.
   - `LoopAgent`: Iterative refinement controller executing `Scheduler` and `BudgetEnforcer` up to 3 times, passing `critic_feedback` on budget violations.
   - `GeminiClient`: Wrapper around Google Gemini API using `GEMINI_API_KEY`, `GEMINI_MODEL`, and `GEMINI_FALLBACK_MODEL` with fallback logic and resilience against API errors.
   - `Skills`: Gemini-assisted enrichment (local gems, day clustering, thematic pacing).

2. **Artifacts & Logging (`services/tracker.py`)**:
   - `artifacts/usages.csv`: Appends run metadata (run ID, timestamp, origin, destination, days, budget, final cost, status, iterations).
   - `artifacts/events.json`: Structured array of fine-grained interaction logs (run ID, timestamp, event type, agent/source, summary, payload).

3. **Web Interface (`app.py`, `templates/`, `static/`)**:
   - **Tab 1: Itinerary Builder & Viewer**:
     - Origin, destination, duration, budget, departure date, interests.
     - Live execution progress and rich itinerary presentation (day-by-day cards, cost breakdowns, map/geo activity clusters).
     - Text and PDF download buttons.
   - **Tab 2: Itineraries & Event Logs**:
     - Metric cards: Total itineraries, successful runs, failed runs, total events.
     - Itinerary Table: Date/time, destination, duration, budget, cost, status, events count button.
     - Row click: Opens modal showing full itinerary.
     - Events count click: Filters and loads the Event Logs Table below for that run.
     - Event Logs Table: Timestamp, event type, agent/source, summary, "Payload" button.
     - Payload Modal: Formatted JSON with a "Copy to Clipboard" button and feedback toast.

---

## Proposed Changes

### Configuration & Utilities

#### [NEW] [config.py](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/travel-itinerary-builder-2/config.py)
- Configuration management: Loads environment variables (`GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL`, `PORT`, `FLASK_DEBUG`).
- Default model fallback setup (e.g., `gemini-2.5-flash` or `gemini-1.5-flash` / `gemini-1.5-pro`).
- Defines artifacts directory paths.

#### [NEW] [requirements.txt](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/travel-itinerary-builder-2/requirements.txt)
- Dependencies: `flask`, `google-genai`, `requests`, `reportlab` (for PDF generation), `python-dotenv`.

---

### Pipeline & Agents

#### [NEW] [pipeline/state.py](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/travel-itinerary-builder-2/pipeline/state.py)
- Data structures and helper methods for the strict Global State Schema:
  - `user_input`, `raw_research`, `current_itinerary`, `critic_feedback`, `budget_approved`.

#### [NEW] [pipeline/gemini_service.py](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/travel-itinerary-builder-2/pipeline/gemini_service.py)
- Centralized Gemini invocation with automatic failover between `GEMINI_MODEL` and `GEMINI_FALLBACK_MODEL`.
- Emits model invocation events for logging.
- Fallback mock data generator if API key is not configured or network unavailable.

#### [NEW] [pipeline/parallel_agent.py](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/travel-itinerary-builder-2/pipeline/parallel_agent.py)
- `ParallelAgent` class: Orchestrates concurrent execution of:
  - `FlightResearcher`: Origin to destination transit options, airline/train tiers, costs.
  - `HotelResearcher`: Accommodations matching budget and interests, neighborhood safety.
  - `ActivityPlanner`: Curated sights, dining, attractions with estimated prices and geographic areas.

#### [NEW] [pipeline/loop_agent.py](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/travel-itinerary-builder-2/pipeline/loop_agent.py)
- `LoopAgent` class: Orchestrates iterative refinement:
  - `Scheduler`: Groups activities geographically by day, incorporates Gemini skills for fun local experiences, incorporates `critic_feedback` from previous loops to reduce costs or replace items.
  - `BudgetEnforcer`: Tallies flights, lodging, and activities. Checks against `budget`. If > budget, calculates deficit, writes concrete `critic_feedback`, and marks `budget_approved = False`. If <= budget, sets `budget_approved = True` and terminates early.
  - Hard limit of 3 iterations; graceful exit if budget is structurally impossible with a clear alert.

#### [NEW] [pipeline/orchestrator.py](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/travel-itinerary-builder-2/pipeline/orchestrator.py)
- Coordinates Sequential Pipeline: `ParallelAgent` -> `LoopAgent` -> Final Assembly and Artifact Logging.

---

### Logging & Artifacts Management

#### [NEW] [services/tracker.py](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/travel-itinerary-builder-2/services/tracker.py)
- Thread-safe event emitter and tracker.
- Manages `artifacts/usages.csv` and `artifacts/events.json`.
- Provides query functions: count metrics, fetch run summaries, fetch specific run events, fetch run payload.

---

### Web App & UI

#### [NEW] [app.py](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/travel-itinerary-builder-2/app.py)
- Flask routes:
  - `GET /`: Main page with tabs.
  - `POST /api/generate`: Submits itinerary request, runs pipeline, returns result JSON.
  - `GET /api/history`: Returns runs and aggregate statistics.
  - `GET /api/history/<run_id>/events`: Returns events for a specific run.
  - `GET /download/txt/<run_id>`: Exports itinerary as formatted plain text.
  - `GET /download/pdf/<run_id>`: Generates and streams a styled PDF itinerary.

#### [NEW] [templates/index.html](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/travel-itinerary-builder-2/templates/index.html)
- Clean, semantic HTML structure with tab navigation (Itinerary Builder vs Itineraries & Event Logs).
- Modals for Full Itinerary View and Event Payload View with clipboard copy.

#### [NEW] [static/css/style.css](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/travel-itinerary-builder-2/static/css/style.css)
- Premium modern styling: subtle glassmorphism, responsive grid, status badges, clean typography, hover transitions.

#### [NEW] [static/js/app.js](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/travel-itinerary-builder-2/static/js/app.js)
- Asynchronous form submission and dynamic rendering of itinerary results.
- Tab switching logic.
- Log table population, filtering by run ID upon clicking event count, modal viewing, and clipboard copy action.

---

## Verification Plan

### Automated & Unit Verification
- Test pipeline state transitions, ParallelAgent execution, LoopAgent feedback refinement cycle, and budget enforcement.
- Test handling of extreme/impossible budgets (e.g. $5 budget for 10 days) to verify graceful failure handling without crashes.
- Verify `artifacts/usages.csv` and `artifacts/events.json` are properly created and formatted.

### Manual / Browser Verification
- Start Flask dev server and test:
  1. Form submission on Tab 1 with realistic parameters (origin, destination, interests, duration, budget).
  2. Rendering of grouped daily activities and cost breakdown.
  3. Text and PDF download functionality.
  4. Tab 2 metric cards and itinerary history table.
  5. Modal popup for full itinerary.
  6. Click events count to reveal filtered event logs table.
  7. Click "Payload" button to open modal, and test "Copy to Clipboard" button.
