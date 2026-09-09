import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

USAGES_CSV = os.path.join(ARTIFACTS_DIR, "usages.csv")
EVENTS_JSON = os.path.join(ARTIFACTS_DIR, "events.json")
RUNS_DIR = os.path.join(ARTIFACTS_DIR, "runs")
os.makedirs(RUNS_DIR, exist_ok=True)

# Gemini configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-1.5-flash")

PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
