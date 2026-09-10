import json
import logging
import os
import re
import sys
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
PRIMARY_MODEL = os.getenv("MODEL_NAME") or os.getenv("MODEL", "gemini-3.5-flash")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gemini-3.5-flash-lite")

if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY or GOOGLE_API_KEY not set in environment or .env file")

client = genai.Client(api_key=GEMINI_API_KEY)
logging.getLogger("google_genai.models").setLevel(logging.ERROR)

# Logging setup
logger = logging.getLogger("skill_logger")
logger.setLevel(logging.DEBUG)
log_path = os.path.join(os.path.dirname(__file__), "skill_real.log")
handler = logging.FileHandler(log_path)
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

# Skill prompt
WEATHER_SKILL = """Role: You are a weather-information assistant.
Process: Follow this sequential process to answer the user query:
  1. THOUGHT: Determine what information is missing.
  2. ACTION: If you need current weather, call the get_weather tool in JSON format:
     Action: {"tool": "get_weather", "arg": "<city name>"}
  3. ANSWER: When you have the observation, provide a concise, friendly answer.

Example Workflow:
Thought: I need the weather for London.
Action: {"tool": "get_weather", "arg": "London"}
Observation: London: 12°C, Light rain.
Thought: I have the data to answer.
Answer: The current weather in London is 12°C with Light rain.
"""

def get_weather(city: str) -> str:
    """Fetch current weather for city using the free wttr.in service."""
    try:
        res = requests.get(f"https://wttr.in/{city}?format=j1", timeout=10, headers={"User-Agent": "skill_real/1.0"})
        res.raise_for_status()
        current = res.json()["current_condition"][0]
        temp_c = current.get("temp_C", "N/A")
        desc = current.get("weatherDesc", [{}])[0].get("value", "")
        return f"{city.title()}: {temp_c}°C, {desc}"
    except Exception as e:
        logger.error("Weather lookup failed for %s: %s", city, e)
        return f"Failed to retrieve weather for {city}."

AVAILABLE_TOOLS = {"get_weather": get_weather}

def generate_content_with_fallback(contents: list[types.Content]) -> str:
    """Call Google Gemini with primary model, falling back gracefully on failure."""
    config = types.GenerateContentConfig(
        system_instruction=WEATHER_SKILL,
        temperature=0.0,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    for model in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            resp = client.models.generate_content(model=model, contents=contents, config=config)
            text = (resp.text or "").strip()
            logger.debug("Model %s response: %s", model, text)
            return text
        except Exception as exc:
            logger.warning("Model %s failed: %s – attempting fallback...", model, exc)
    return ""

def run_agent_loop(user_query: str) -> None:
    """Execute the ReAct reasoning loop with tool invocation."""
    print(f"🚀 User Query: '{user_query}'\n")
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=f"User Query: {user_query}")])]

    for step in range(1, 5):
        print(f"--- [Loop Iteration {step}] ---")
        reply = generate_content_with_fallback(contents)
        print(reply)

        contents.append(types.Content(role="model", parts=[types.Part.from_text(text=reply)]))

        action_match = re.search(r"Action:\s*(\{.*?\})", reply, re.DOTALL) or re.search(r"(\{.*\"tool\".*?\})", reply, re.DOTALL)
        if action_match:
            try:
                call = json.loads(action_match.group(1))
                tool_fn = AVAILABLE_TOOLS.get(call.get("tool"))
                observation = tool_fn(call.get("arg", "")) if tool_fn else f"Tool '{call.get('tool')}' not found."
            except Exception as e:
                observation = f"Failed to parse or execute action: {e}"

            print(f"🔍 [Tool Output/Observation]: {observation}")
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=f"Observation: {observation}")]))
        else:
            print("\n✅ Task completed successfully!")
            return

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:]).strip()
    else:
        try:
            query = input("Enter your weather query (or press Enter for default): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

    if not query:
        query = "What is the weather in London?"
        print(f"Using default query: '{query}'\n")

    run_agent_loop(query)
