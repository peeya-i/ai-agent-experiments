# Implementation Plan: Itinerary History & Event Logs View

Implement a top-level view selectable by clicking a tab at the top of the screen that displays two coordinated tables:
1. **Top Table**: A list of all created itineraries (destination, origin, duration, budget, cost, approval status, event count, timestamp).
2. **Bottom Box / Table**: A list of events and logs that occurred during the creation of the specifically selected itinerary from the top table.

## User Review Required

> [!NOTE]
> The top navigation tabs will allow seamless switching between the **Trip Planner** view (the form, live agent pipeline visualizer, and results) and the new **Itineraries & Event Logs** view.

## Proposed Changes

### Backend & API Layer

#### [MODIFY] [pipeline/event_logger.py](file:///home/pi-net/Documents/agent_eng_labs/agent_engineering/my-apps/travel-Itinerary-builder/pipeline/event_logger.py)
- Implement `get_all_itineraries_with_events(file_path=None)`:
  - Parses `artifacts/events.json` (and `artifacts/usages.csv`).
  - Groups sequential events into discrete itinerary creation sessions (from `pipeline_start` through `pipeline_complete` / `pipeline_fallback`).
  - Formats rich metadata: `id`, `start_time`, `end_time`, `destination`, `origin`, `budget`, `days`, `interests`, `departure_date`, `total_estimated_cost`, `budget_approved`, `status`, `events`, and `logs`.
  - Supports reverse-chronological ordering (most recent first).

#### [MODIFY] [pipeline/runner.py](file:///home/pi-net/Documents/agent_eng_labs/agent_engineering/my-apps/travel-Itinerary-builder/pipeline/runner.py)
- Ensure all future pipeline executions generate and attach a persistent `itinerary_id` to every event logged to `events.json` and `usages.csv`.

#### [MODIFY] [app.py](file:///home/pi-net/Documents/agent_eng_labs/agent_engineering/my-apps/travel-Itinerary-builder/app.py)
- Add API endpoints:
  - `GET /api/itineraries`: Returns JSON array of all created itineraries with summary statistics.
  - `GET /api/itineraries/<itinerary_id>`: Returns detailed data for a specific itinerary including its complete event stream and agent activity logs.

---

### Frontend UI & Aesthetics

#### [MODIFY] [templates/index.html](file:///home/pi-net/Documents/agent_eng_labs/agent_engineering/my-apps/travel-Itinerary-builder/templates/index.html)
- Add top navigation tabs in the header:
  - **Trip Planner** (`tab-nav-btn active`) with icon `<i class="fa-solid fa-map-location-dot"></i>`
  - **Itineraries & Event Logs** (`tab-nav-btn`) with icon `<i class="fa-solid fa-table-list"></i>` and dynamic count badge.
- Add `<section id="viewHistory" class="view-section">`:
  - **First Table (Top Box)**: Created Itineraries Table
    - Header with search, status filters (All, Approved, Over Budget, Fallback), and Refresh button.
    - Table columns: `ID`, `Created Date`, `Destination`, `Duration`, `Budget`, `Estimated Cost`, `Status / Approval`, `Events Count`, `Action`.
    - Active row highlighting and empty state.
  - **Second Box (Bottom Box)**: Selected Itinerary Events & Logs
    - Header showing selected itinerary details (`Destination`, `ID`, `Date`, `Duration`, `Status`).
    - Event filter chips (`All Events`, `Model Requests`, `Model Responses`, `Tool Calls`, `Tool Responses`, `Pipeline Steps`).
    - Events Table with columns: `#`, `Time`, `Event Type (Badge)`, `Agent / Source`, `Summary / Action Details`, `Payload (Inspect)`.
    - Integrated log viewer panel for textual agent logs.
    - Modal popup to view formatted JSON payloads for any event.

#### [MODIFY] [static/css/style.css](file:///home/pi-net/Documents/agent_eng_labs/agent_engineering/my-apps/travel-Itinerary-builder/static/css/style.css)
- Add styling for:
  - Top navigation tab bar and active glow indicators.
  - Glassmorphic table containers with sticky headers, custom scrollbars, and alternating row highlights.
  - Table selection states with glowing borders and active indicator arrows.
  - Color-coded event badges (`model_request`, `model_response`, `tool_call`, `tool_response`, `skill_invocation`, `pipeline_start`, `pipeline_complete`, `pipeline_fallback`).
  - JSON payload inspection modal and responsive table design.

#### [MODIFY] [static/js/app.js](file:///home/pi-net/Documents/agent_eng_labs/agent_engineering/my-apps/travel-Itinerary-builder/static/js/app.js)
- Handle top tab navigation switching between Trip Planner and Itineraries & Event Logs.
- Fetch and render itineraries from `/api/itineraries`.
- Implement selection handler for the top table:
  - Updates active row style.
  - Dynamically populates the bottom table with the selected itinerary's events and logs.
  - Supports filtering events by event type or searching event summaries.
  - Implements JSON inspector modal for viewing full event payloads.
- Automatically refresh history when a new itinerary is created.

---

### Testing & Verification

#### [NEW] [tests/test_history.py](file:///home/pi-net/Documents/agent_eng_labs/agent_engineering/my-apps/travel-Itinerary-builder/tests/test_history.py)
- Test `/api/itineraries` and `/api/itineraries/<id>` endpoints.
- Verify event grouping from `events.json`.
- Test empty state handling and selection edge cases.

## Verification Plan

### Automated Tests
- Run `.venv/bin/python -m unittest discover -s tests -p "test_*.py"` to ensure all tests pass.

### Manual Verification
1. Launch Flask app and navigate to `http://localhost:5000` (or configured port).
2. Click the top navigation tab **"Itineraries & Event Logs"**.
3. Verify the top table displays the list of 31+ created itineraries from `events.json`.
4. Click on various itinerary rows in the top table (e.g. `Mumbai, India`, `Chiangrai, Thailand`, `Mexico`).
5. Verify the bottom box updates immediately to show the events and logs for that specific selected itinerary.
6. Test event filters (Model Requests, Tool Invocations, etc.) and click "Inspect Payload" to verify JSON modal.
7. Switch back to "Trip Planner", generate a new itinerary, and switch to "Itineraries & Event Logs" to verify the new itinerary appears and its events/logs are selectable.
