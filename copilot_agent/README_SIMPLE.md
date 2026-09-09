# Simple Gemini AI Agent

`simple_AI_agent.py` is a terminal-based AI agent powered by Google Gemini. It accepts natural-language prompts, answers general questions, provides recommendations, and can use a tool to answer two private house questions:

- House color: blue
- House city: San Jose

## Setup

1. Activate the virtual environment:

   ```bash
   source .venv/bin/activate
   ```

2. Install the dependencies if needed:

   ```bash
   pip install google-genai python-dotenv
   ```

3. Create `.env` from `.env.example` and set your Google AI Studio key:

   ```dotenv
   GOOGLE_API_KEY=your_google_api_key
   MODEL=gemini-2.5-flash
   ```

   Do not commit `.env` or place the key in source code.

## Run

From this directory, run:

```bash
python simple_AI_agent.py
```

Type a question at the `You:` prompt. Enter `quit` or `exit` to stop.

Examples:

```text
You: What color is my house?
You: Which city is my house in?
You: Recommend a weekend activity in San Jose.
```

## Logging

The agent writes human-readable interaction records to `simple_AI_agent.log`. Each prompt starts with `=== PROMPT ===`. The log includes requests and responses exchanged between the user, agent, Gemini model, and private-house tool, including function-call payloads. The configured Google API key is redacted before messages are written to the log.