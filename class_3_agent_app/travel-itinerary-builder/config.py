"""Configuration module for Travel Itinerary Builder."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from current directory or parent directory
BASE_DIR = Path(__file__).resolve().parent
dotenv_path = BASE_DIR / ".env"
if not dotenv_path.exists():
    # Try finding .env in parent directories if not in current
    for parent in BASE_DIR.parents:
        if (parent / ".env").exists():
            dotenv_path = parent / ".env"
            break

load_dotenv(dotenv_path=dotenv_path, override=True)

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Flask configuration
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("FLASK_ENV", "development").lower() == "development"
