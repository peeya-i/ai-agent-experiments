"""Terminal Gemini agent that follows skill.md for weather and local time."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "skill_AI_agent.log"
SKILL_FILE = BASE_DIR / "skill.md"
load_dotenv(BASE_DIR / ".env")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv(
	"OPENWEATHERMAP_API_KEY", os.getenv("OPENWEATHER_API_KEY", "")
)
MODEL = os.getenv("MODEL", "gemma-4-26b-a4b-it")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gemini-3.5-flash-lite")
SKILL_INSTRUCTIONS = SKILL_FILE.read_text(encoding="utf-8")


class ApiKeyRedactingFilter(logging.Filter):
	def filter(self, record: logging.LogRecord) -> bool:
		message = record.getMessage()
		for key in (GOOGLE_API_KEY, OPENWEATHER_API_KEY):
			if key:
				message = message.replace(key, "[REDACTED_API_KEY]")
		record.msg = message
		record.args = ()
		return True


logger = logging.getLogger("skill_AI_agent")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
handler.addFilter(ApiKeyRedactingFilter())
logger.addHandler(handler)


@dataclass
class InteractionEvent:
	sender: str
	recipient: str
	message_type: str
	payload: Any


def to_loggable(value: Any) -> Any:
	if hasattr(value, "model_dump"):
		return to_loggable(value.model_dump(exclude_none=True))
	if hasattr(value, "to_json_dict"):
		return to_loggable(value.to_json_dict())
	if isinstance(value, dict):
		return {str(key): to_loggable(item) for key, item in value.items()}
	if isinstance(value, (list, tuple)):
		return [to_loggable(item) for item in value]
	return value


def log_event(sender: str, recipient: str, message_type: str, payload: Any) -> None:
	event = InteractionEvent(sender, recipient, message_type, payload)
	header = f"{sender.upper()} -> {recipient.upper()} [{message_type}]"
	body = json.dumps(to_loggable(asdict(event)["payload"]), default=str, ensure_ascii=False, indent=2)
	logger.info("%s\n%s", header, body)


def log_prompt(user_input: str) -> None:
	logger.info("=== PROMPT ===")
	log_event("user", "agent", "input", {"text": user_input})


def http_get_json(url: str) -> dict[str, Any]:
	log_event("skill", "external_service", "request", {"url": url})
	request = Request(url, headers={"User-Agent": "skill_AI_agent/1.0"})
	try:
		with urlopen(request, timeout=15) as response:
			result = json.load(response)
		log_event("external_service", "skill", "response", result)
		return result
	except (HTTPError, URLError, TimeoutError) as error:
		raise RuntimeError(f"External request failed: {error}") from error


def get_weather(city: str) -> dict[str, Any]:
	if not OPENWEATHER_API_KEY:
		raise RuntimeError("OPENWEATHERMAP_API_KEY is not configured in .env.")
	url = (
		"https://api.openweathermap.org/data/2.5/weather"
		f"?q={quote(city)}&appid={quote(OPENWEATHER_API_KEY)}&units=metric"
	)
	data = http_get_json(url)
	return {
		"city": data.get("name", city),
		"country": data.get("sys", {}).get("country"),
		"temperature_c": data.get("main", {}).get("temp"),
		"feels_like_c": data.get("main", {}).get("feels_like"),
		"condition": (data.get("weather") or [{}])[0].get("description"),
		"humidity_percent": data.get("main", {}).get("humidity"),
		"wind_speed_mps": data.get("wind", {}).get("speed"),
	}


CITY_TIMEZONES = {
	"san jose": "America/Los_Angeles",
	"new york": "America/New_York",
	"london": "Europe/London",
	"paris": "Europe/Paris",
	"tokyo": "Asia/Tokyo",
	"sydney": "Australia/Sydney",
	"singapore": "Asia/Singapore",
	"dubai": "Asia/Dubai",
}


def get_local_time(city: str) -> dict[str, Any]:
	timezone = CITY_TIMEZONES.get(city.strip().lower())
	if not timezone:
		raise RuntimeError(f"No timezone mapping is configured for {city!r}.")
	data = http_get_json(f"https://worldtimeapi.org/api/timezone/{quote(timezone, safe='/')}")
	return {
		"city": city,
		"timezone": data.get("timezone", timezone),
		"datetime": data.get("datetime"),
		"utc_offset": data.get("utc_offset"),
	}


def get_private_house_information(question: str) -> dict[str, str]:
	normalized = question.lower()
	if "color" in normalized or "colour" in normalized:
		return {"answer": "blue"}
	if any(word in normalized for word in ("city", "where", "location")):
		return {"answer": "San Jose"}
	return {"answer": "I can only answer the house color or city."}


SKILL_TOOLS = types.Tool(function_declarations=[
	types.FunctionDeclaration(
		name="get_weather",
		description="Get current weather for a city using the OpenWeatherMap skill.",
		parameters=types.Schema(type=types.Type.OBJECT, properties={"city": types.Schema(type=types.Type.STRING)}, required=["city"]),
	),
	types.FunctionDeclaration(
		name="get_local_time",
		description="Get local time for a city using the WorldTimeAPI skill.",
		parameters=types.Schema(type=types.Type.OBJECT, properties={"city": types.Schema(type=types.Type.STRING)}, required=["city"]),
	),
	types.FunctionDeclaration(
		name="get_private_house_information",
		description="Answer a private question about the user's house color or city.",
		parameters=types.Schema(type=types.Type.OBJECT, properties={"question": types.Schema(type=types.Type.STRING)}, required=["question"]),
	),
])

TOOL_FUNCTIONS = {
	"get_weather": get_weather,
	"get_local_time": get_local_time,
	"get_private_house_information": get_private_house_information,
}


def describe_tools() -> list[dict[str, Any]]:
	return [
		{"name": item.name, "description": item.description, "parameters": to_loggable(item.parameters)}
		for item in SKILL_TOOLS.function_declarations or []
	]


def ask_agent(client: genai.Client, user_input: str, model: str) -> str:
	contents: list[types.Content] = [types.Content(role="user", parts=[types.Part.from_text(text=user_input)])]
	config = types.GenerateContentConfig(
		tools=[SKILL_TOOLS],
		system_instruction=(
			"You are a helpful terminal assistant. Follow the active skill instructions "
			"for weather and local-time questions. Use the private-house tool for house questions.\n\n"
			f"Active skill instructions:\n{SKILL_INSTRUCTIONS}"
		),
	)
	for _ in range(5):
		log_event("agent", "llm", "request", {
			"model": model,
			"system_instruction": config.system_instruction,
			"available_tools": describe_tools(),
			"contents": to_loggable(contents),
		})
		response = client.models.generate_content(model=model, contents=contents, config=config)
		calls = response.function_calls or []
		log_event("llm", "agent", "response", {
			"text": response.text,
			"function_calls": [{"name": call.name, "args": call.args} for call in calls],
			"response_details": to_loggable(response),
		})
		if not calls:
			return response.text or "I could not produce a response."
		contents.append(response.candidates[0].content)
		results = []
		for call in calls:
			arguments = call.args or {}
			log_event("agent", "skill/tool", call.name, arguments)
			try:
				result = TOOL_FUNCTIONS[call.name](**arguments)
			except Exception as error:
				result = {"error": str(error)}
			log_event("skill/tool", "agent", call.name, result)
			results.append(types.Part.from_function_response(name=call.name, response=result))
		contents.append(types.Content(role="user", parts=results))
	raise RuntimeError("The model requested too many tool calls.")


def main() -> None:
	if not GOOGLE_API_KEY:
		raise RuntimeError("GOOGLE_API_KEY is not set. Add it to .env or the environment.")
	client = genai.Client(api_key=GOOGLE_API_KEY)
	model = MODEL
	print("Skill Gemini agent. Ask about weather, local time, or your house. Type 'quit' to stop.")
	while True:
		try:
			user_input = input("You: ").strip()
		except (EOFError, KeyboardInterrupt):
			print()
			break
		if not user_input:
			continue
		if user_input.lower() in {"quit", "exit"}:
			break
		try:
			log_prompt(user_input)
			try:
				output = ask_agent(client, user_input, model)
			except Exception as first_error:
				if model == FALLBACK_MODEL:
					raise
				log_event("agent", "fallback", "model_error", str(first_error))
				model = FALLBACK_MODEL
				output = ask_agent(client, user_input, model)
			print(f"Agent: {output}")
			log_event("agent", "user", "output", output)
		except Exception as error:
			output = f"I could not complete that request: {error}"
			print(f"Agent: {output}")
			log_event("agent", "user", "error", output)


if __name__ == "__main__":
	main()
