"""FastAPI Web Application and API Orchestrator for Structured Multi-Skill AI Agent.

Provides:
- 2-page web interface (Page 1: Chat with Agent, Page 2: Log Review)
- REST API for chat interactions, conversation audits, and detailed event inspections.
"""

import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# Ensure local directories and skills are importable
BASE_DIR = Path(__file__).parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agent import get_agent

try:
    from logging import (
        get_conversations,
        get_conversation_events,
        get_event_detail,
        log_event,
    )
except ImportError:
    import importlib.util
    spec = importlib.util.spec_from_file_location("local_logging", BASE_DIR / "logging.py")
    _lmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_lmod)
    get_conversations = _lmod.get_conversations
    get_conversation_events = _lmod.get_conversation_events
    get_event_detail = _lmod.get_event_detail
    log_event = _lmod.log_event

app = FastAPI(
    title="Structured Multi-Skill AI Agent",
    description="Autonomous AI Agent utilizing Google GenAI SDK, domain skills, and asynchronous audit logs.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_cache_control_header(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# Mount static files
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    model_used: str


@app.get("/")
async def get_index():
    """Serve main 2-page web application."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found.")
    return FileResponse(str(index_file))


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    """Chat endpoint to process user queries through multi-skill agent orchestrator."""
    query = payload.message.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        agent = get_agent()
        result = await agent.run(
            user_query=query,
            conversation_id=payload.conversation_id,
            model=payload.model,
        )
        return ChatResponse(
            conversation_id=result["conversation_id"],
            response=result["response"],
            model_used=result["model_used"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations")
async def list_conversations():
    """Retrieve all conversations for Page 2 Log Review (Table 1)."""
    try:
        conversations = get_conversations()
        return {"status": "success", "conversations": conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations/{conversation_id}/events")
async def list_conversation_events(conversation_id: str):
    """Retrieve events for a specific conversation for Page 2 Log Review (Table 2)."""
    try:
        events = get_conversation_events(conversation_id)
        return {"status": "success", "conversation_id": conversation_id, "events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/events/{event_id}")
async def event_detail(event_id: str):
    """Retrieve detailed human-readable JSON payload for the pop-up modal."""
    event = get_event_detail(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    return {"status": "success", "event": event}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting Multi-Skill Agent Web Server on http://0.0.0.0:{port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
