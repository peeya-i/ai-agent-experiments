# Walkthrough: Travel Itinerary Builder

The **Travel Itinerary Builder** application has been implemented according to all specifications outlined in [SPECIFICATIONS.md](file:///home/pi-net/Documents/agent_eng_labs/agent_engineering/my-work/travel-Itinerary-builder/SPECIFICATIONS.md), including comprehensive JSON event logging.

---

## 🌟 What Was Built

### 1. JSON Event Logging (`artifacts/events.json`, `pipeline/event_logger.py`)
- Automatically records **all messages sent to Gemini models**, **all model responses**, **all tool executions**, and **pipeline lifecycle events** into [artifacts/events.json](file:///home/pi-net/Documents/agent_eng_labs/agent_engineering/my-apps/travel-Itinerary-builder/artifacts/events.json) in **single-line JSON (JSON Lines)** format.
- Recorded event types:
  - `model_request`: Outgoing prompt, history, system instructions, model parameters.
  - `model_response`: Incoming LLM text, model versions, usage metadata, and function calls.
  - `tool_call` & `tool_execution`: Tool names, input arguments, and parameters.
  - `tool_response`: Tool return values, execution confirmations, and state deltas.
  - `pipeline_start` & `pipeline_complete`: User preferences and final synthesized itinerary.

### 2. Multi-Agent Pipeline (`pipeline/agents.py`, `pipeline/tools.py`)
- **Sequential Pipeline**: Implemented via `SequentialAgent(name="TravelItineraryPipeline", sub_agents=[DiscoveryTeam, OptimizationRoom])`.
- **Parallel Discovery Team**: Implemented via `ParallelAgent` running 3 concurrent sub-agents:
  - `FlightResearcher`: Researches transport, travel times, and roundtrip costs.
  - `HotelResearcher`: Finds lodging options across luxury, mid-range, and budget tiers matching safety and location.
  - `ActivityPlanner`: Compiles curated landmarks, restaurants, and tours matching user interests.
- **Loop Optimization Room**: Implemented via `LoopAgent` (max 5 iterations):
  - `Scheduler`: Synthesizes raw research into a day-by-day itinerary and reads `critic_feedback` from prior iterations to adjust hotel tiers, select cheaper/free activities, and optimize dining costs.
  - `BudgetEnforcer`: Validates `total_estimated_cost` against `budget`. If within budget, sets `budget_approved = True` and exits the loop; if over budget, provides actionable `critic_feedback` and triggers the next iteration.

### 3. Centralized Global State Schema (`pipeline/state.py`)
Conforms to the exact dictionary schema:
- `user_input`: destination, budget, days, interests
- `raw_research`: flights, hotels, activities
- `current_itinerary`: total_estimated_cost, schedule
- `critic_feedback`: string
- `budget_approved`: boolean

### 4. Flask Web Application & Modern UI (`app.py`, `templates/`, `static/`)
- **Form validation**: Missing fields prompt the user with clear inline messages.
- **Dynamic visual tracker**: Real-time agent status badges for Discovery Team and Optimization Room.
- **Rich results view**:
  - Trip overview & budget variance card
  - Day-by-Day interactive schedule timeline
  - Research discovery breakdown (flight, lodging, and activity choices)
  - Budget allocation summary
  - Export / Print / Copy JSON state features

---

## 🧪 Verification & Test Results

All unit and integration tests passed:

```bash
$ python -m unittest discover -s tests -p "test_*.py"
.....
----------------------------------------------------------------------
Ran 5 tests in 3.369s

OK
```
