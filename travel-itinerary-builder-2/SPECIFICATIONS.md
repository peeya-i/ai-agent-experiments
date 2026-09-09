# Travel Itinerary Builder

## Overview
Build Travel Itinerary Builder as an autonomous, multi-agent AI pipeline designed to generate structured, multi-day vacation plans.

Build the app to use Gemini API. Use flask to build this application.

The app should have 2 pages selectable using the tab bar at the top of the page.

### Page 1: Generate Itinerary
- The user should be able to input:
  - city of origin
  - destination
  - interests
  - budget
  - departure date (optional)
  - duration
- After the user submits the form, the app will display:
  - The generated itinerary should be shown in a detailed, day-by-day format. Each day should be clearly separated and include:
    - The day number and the estimated cost for that day.
    - The activity should suggest where to eat for all meals for the day including the breakfast, lunch, and dinner. 
    - The time slot for each activity.
    - The name of the activity.
    - The estimated cost for each activity.
    - The duration for each activity.
    - The location of each activity.
    - Any other relevant information about the activity.
  - A status indicator showing the current step in the itinerary generation process.
  - The app will group the activities geographically each day to prevent excessive travel time.
  - The app will enforce strict budgetary boundaries.
  - The generated itinerary should be displayed in a user-friendly format in the same page.
- Create a button to allow the user to download the generated itinerary as a text or PDF file.

### Page 2: Itineraries & Events Logs
This page is for displaying the past Itineraries and Event logs.
- At the top of the page, there should be a summary of the number of itineraries requested, the number of itineraries generated, failed requests, and the number of events logged.
- Below the summary, there should be two tables.
- The first table should show the list of itineraries requested. Each row of the itinerary should show the request details including the date and time it was created, the travel date, the duration,  the destination, the city of origin, the budget, the estimated cost, status of the request, and the number of event logs created for that run.
  - When the row is clicked, it should display the full itinerary for that run in a pop up window.
  - When the events count in each row is clicked, all the event logs for that run should be shown in the second table below the itinerary table.

- Each row of the event log should show the details for each request including the timestamp, event type, agent/source of the event, a short summary of the event log, and a "Payload" button to show details about the event log.
  - When the "Payload" button is clicked, it should display the full and complete payloads for that event log in a pop up window.
  - The pop up window should display all information stored in the event
  - It should include a "Copy to Clipboard" button to allow the user to copy the contents of the payload to the clipboard.

## Other Requirements
- The app should get the API Key from the environment variable GEMINI_API_KEY, model name from the environment variable GEMINI_MODEL, and fallback model name from the environment variable GEMINI_FALLBACK_MODEL. Use the fallback model name if the primary model name is not available.
- The app should store the information from each user request in a CSV file named usages.csv in the artifacts folder.
- The app should store the events and interactions including the **full and complete** payloads between the agent, skills, tools, LLM models, and etc in a file named events.json in the artifacts folder.
  - Each entry in the events.json file should be a separate JSON object, on its own line.
  - The app should redact the API Key from the event payload before storing it in the events.json file. 
- Create a README.md file to show how to run the app and how the app works

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
- **Cap:** Maximum of 3 iterations.

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
