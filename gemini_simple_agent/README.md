# Simple AI Agent (Google Gemini)

A conversational AI agent built with Python and the official Google GenAI SDK (`google-genai`). The agent accepts natural language inputs from the terminal, answers general questions, provides recommendations, and uses a dedicated function tool to query private information about the user's house. All communications between the agent, LLM, and tools are structured and logged with API key redaction.

---

## Features

- **Interactive Terminal Interface**: Continuously reads natural language input from the command line until instructed to exit.
- **Google Gemini Model Integration**: Communicates with Google Gemini / Gemma models using the modern `google-genai` SDK.
- **General Questions & Recommendations**: Answers knowledge questions, provides structured advice, and delivers helpful recommendations.
- **Private House Tool**: Integrates `get_private_house_information` to privately query:
  - **House Color**: `blue`
  - **House City**: `San Jose`
- **Comprehensive & Structured Logging**:
  - Automatically logs every message exchanged between the **Agent**, **LLM**, and **Tools**.
  - Captures the exact request and response payloads (in human-readable JSON format).
  - Prepends each prompt cycle with a distinct `=== PROMPT ===` marker line.
  - Automatically redacts API keys and sensitive tokens for security.

---

## Project Structure

```
gemini_simple_agent/
├── simple_AI_agent.py          # Main application script
├── simple_AI_Instructions.yaml # Agent specifications and requirements
├── README.md                   # Project documentation and usage guide
├── .env.example                # Example environment variable configuration
├── .env                        # Local environment variables (API keys)
├── .gitignore                  # Git ignore rules for logs, virtualenv, and secrets
├── simple_AI_agent.log         # Generated structured execution log
└── .venv/                      # Python virtual environment
```

---

## Prerequisites

- **Python**: Version 3.10 or later (Python 3.14 supported).
- **Google Gemini API Key**: Obtainable from [Google AI Studio](https://aistudio.google.com/).

---

## Setup & Installation

1. **Navigate to the project directory**:
   ```bash
   cd /home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/gemini_simple_agent
   ```

2. **Activate the virtual environment** (or create one if needed):
   ```bash
   # If creating a new virtual environment:
   python3 -m venv .venv

   # Activate the virtual environment:
   source .venv/bin/activate
   ```

3. **Install required dependencies**:
   ```bash
   pip install google-genai python-dotenv
   ```

4. **Configure Environment Variables**:
   Copy `.env.example` to `.env` (if not already present):
   ```bash
   cp .env.example .env
   ```
   Open `.env` and set your Google API key:
   ```ini
   GOOGLE_API_KEY=your_actual_google_api_key_here
   MODEL="gemini-3.5-flash-lite"
   FALLBACK_MODEL="gemini-3.5-flash"
   ```
   *(Note: You can also configure `MODEL="gemma-4-26b-a4b-it"` or other available models supported by your API key).*

---

## How to Run the Code

Run the agent script directly from your terminal:

```bash
python simple_AI_agent.py
```

Or using the virtual environment interpreter:

```bash
.venv/bin/python simple_AI_agent.py
```

### Exiting the Application
Type `quit` or `exit`, or press `Ctrl+C` / `Ctrl+D` at any time to cleanly exit the session.

---

## Example Interactions

### 1. General Questions & Recommendations
```
You: Can you recommend two books on machine learning?
Agent: Certainly! Here are two highly recommended books on machine learning:
1. "Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow" by Aurélien Géron...
2. "Pattern Recognition and Machine Learning" by Christopher Bishop...
```

### 2. Private House Inquiries (Invoking Tool)
```
You: What color is my house?
Agent: Your house is blue!

You: Where is my house located?
Agent: Your house is located in San Jose.

You: Tell me about my house color and city location.
Agent: Your house is blue and is located in San Jose.
```

---

## Logging & Security

All interactions are recorded in `simple_AI_agent.log` (and mirrored to `ai_agent.log`).

### Key Log Characteristics:
1. **Prompt Separator**: Every query is initiated with:
   ```
   === PROMPT ===
   ```
2. **Directional Tracking**:
   - `USER -> AGENT (PROMPT_REQUEST)`
   - `AGENT -> LLM (GENERATE_CONTENT_REQUEST)`
   - `LLM -> AGENT (GENERATE_CONTENT_RESPONSE)`
   - `AGENT -> TOOL:get_private_house_information (TOOL_REQUEST)`
   - `TOOL:get_private_house_information -> AGENT (TOOL_RESPONSE)`
   - `AGENT -> USER (FINAL_RESPONSE)`
3. **Payload Inspection**: The complete JSON payloads for requests and responses are captured with 2-space indentation.
4. **Security & Redaction**: `ApiKeyMaskingFilter` intercepts log records and substitutes API keys with `[REDACTED_API_KEY]`, `[REDACTED_GOOGLE_API_KEY]`, or `[REDACTED_KEY]`.
