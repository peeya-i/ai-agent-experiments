# Travel Itinerary Builder

## Overview
Build Travel Itinerary Builder as an autonomous, multi-agent AI pipeline designed to generate structured, multi-day vacation plans. The system takes user preferences (city of origin, destination, budget, duration, interests and optional departure date) and produces a complete itinerary while cross-referencing scheduling conflicts and enforcing strict budgetary boundaries. Build the app to use Gemini API. It should get the API Key from the environment variable GEMINI_API_KEY and model name from the environment variable GEMINI_MODEL.

Use flask to build the frontend for this application. The app will ask for the destination, budget, departure date, duration, and interests. If the information is missing, it will prompt the user to provide it. If the data is valid, the app will call the backend API to generate the itinerary and display it in a user-friendly format.

Store the information from each user request in a CSV file named usages.csv in the artifacts folder. Each row should have the following columns: timestamp, event_type, user_input, prompt, agent, model, request_contents, config, response, debug_log. Add the response to the CSV file. All the fields can be of type string. You can use "a" mode to append the data to the CSV file.

## Architecture
The application follows a hybrid orchestration pattern, utilizing a **Sequential Pipeline** that coordinates a **Parallel Discovery Phase** followed by an iterative **Loop Refinement Phase**.

### 1. Parallel Agent (Discovery Team)
Orchestrated by the `ParallelAgent`, the following sub-agents execute concurrently:
- **FlightResearcher:** Locates transport, travel times, and costs.
- **HotelResearcher:** Finds lodging matching interests and neighborhood safety.
- **ActivityPlanner:** Compiles landmarks, restaurants, and tours.

### 3. Loop Agent (Optimization Room)
Orchestrated by the `LoopAgent`, these agents refine the itinerary:
- **Scheduler:** Reads research, builds the day-by-day sequence, group daiy activities to make sure they are geographically close and efficient to travel between, and calculates total costs. Implement Gemini skills in this agent to make the itinerary more interesting and fun for the user.
- **BudgetEnforcer:** Validates the itinerary against the user's budget.

### Loop Constraints
- **Success:** If cost ≤ budget, `budget_approved` is set to `true` and the loop terminates.
- **Failure:** If cost > budget, the agent provides `critic_feedback` (e.g., "Replace 5-star hotel with 3-star"), sets `budget_approved` to `false`, and triggers the Scheduler for the next iteration.
- **Cap:** Maximum of 5 iterations.

## Global State Schema
All agents interact with a single, centralized dictionary state:

```json
{
  "user_input": {
    "destination": "string",
    "budget": "float",
    "days": "integer",
    "interests": ["string"]
  },
  "raw_research": {
    "flights": [],
    "hotels": [],
    "activities": []
  },
  "current_itinerary": {
    "total_estimated_cost": "float",
    "schedule": [
      {
        "day": "integer",
        "events": []
      }
    ]
  },
  "critic_feedback": "string",
  "budget_approved": "boolean"
}
```

##  Quality Evaluation

The implementation is evaluated based on three milestones:

- **Structural Integrity (40%)**: Must explicitly declare ParallelAgent and LoopAgent frameworks.
- **Context Extraction & State Management (40%)**: The Scheduler must read critic_feedback from prior iterations to modify the trip successfully.
- **Graceful Failure Handling (20%)**: Must handle impossible inputs (e.g., extremely low budgets) without crashing.
