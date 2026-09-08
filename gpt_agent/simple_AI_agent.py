# simple_AI_agent.py
"""
Simple AI Agent
Implements a terminal interface that accepts natural language input, forwards it to the Google Gemini model, and provides basic responses.
It also includes a built-in tool for answering two private questions about the user's house:
- The color of the house (blue)
- The city where the house is located (San Jose)
All interactions are logged to a human‑readable log file with the API key masked.
"""

import os
import json
import datetime
import sys
from typing import Any
from dotenv import load_dotenv

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("MODEL", "gemini-1.5-flash")
FALLBACK_MODEL_NAME = os.getenv("FALLBACK_MODEL")
if not API_KEY:
    print("[!] GOOGLE_API_KEY environment variable not set.")
    sys.exit(1)

# Masked version used for logging – never write the raw key
MASKED_API_KEY = "<API_KEY>"

# Log file path – same directory as this script
LOG_PATH = os.path.join(os.path.dirname(__file__), "ai_agent.log")

# ------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------

def _log(entry: dict) -> None:
    """Append a JSON line to the log file.

    The log is deliberately simple: each line is a JSON object containing
    a timestamp and a free‑form ``type`` field describing the kind of
    message (prompt, response, tool‑call, etc.).  The API key is masked.
    """
    entry["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def _log_prompt(prompt: str) -> None:
    _log({"type": "prompt", "content": prompt, "separator": "=== PROMPT ==="})

def _log_response(response: str) -> None:
    _log({"type": "response", "content": response})

def _log_tool(name: str, query: str, answer: str) -> None:
    _log({"type": "tool", "tool_name": name, "query": query, "answer": answer})

# ------------------------------------------------------------
# Private‑question tool
# ------------------------------------------------------------

def _private_house_tool(question: str) -> str:
    """Answer the two hard‑coded private house questions.

    The function matches the intent loosely; if the question mentions
    "color" and "house" we return the colour, if it mentions "city" and
    "house" we return the city.  Any other query falls back to the LLM.
    """
    lowered = question.lower()
    if "color" in lowered and "house" in lowered:
        answer = "The house is blue."
        _log_tool("private_house", question, answer)
        return answer
    if "city" in lowered and "house" in lowered:
        answer = "The house is located in San Jose."
        _log_tool("private_house", question, answer)
        return answer
    return ""

# ------------------------------------------------------------
# Gemini integration
# ------------------------------------------------------------
try:
    import google.generativeai as genai
except ImportError:
    print("[!] google-generativeai package not installed. Install with `pip install google-generativeai`.")
    sys.exit(1)

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

def _call_gemini(user_input: str) -> str:
    """Send *user_input* to Gemini, trying primary then fallback model."""
    last_error = None
    for name in [MODEL_NAME, FALLBACK_MODEL_NAME]:
        if not name:
            continue
        try:
            model = genai.GenerativeModel(name)
            response = model.generate_content(user_input)
            return response.text.strip()
        except Exception as e:
            last_error = e
    return f"[Error communicating with Gemini: {last_error}]"
    """Send *user_input* to Gemini and return the textual response."""
    try:
        response = model.generate_content(user_input)
        return response.text.strip()
    except Exception as e:
        return f"[Error communicating with Gemini: {e}]"

# ------------------------------------------------------------
# Main interaction loop
# ------------------------------------------------------------
def main() -> None:
    print("Simple AI Agent – type your question (Ctrl‑C to quit)")
    while True:
        try:
            user_input = input("\n>>> ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break
        _log_prompt(user_input)
        private_answer = _private_house_tool(user_input)
        response = private_answer if private_answer else _call_gemini(user_input)
        print("\n[Agent]:", response)
        _log_response(response)

if __name__ == "__main__":
    main()
