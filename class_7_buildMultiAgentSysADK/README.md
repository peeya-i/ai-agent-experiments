# Movie Script & Screenplay Multi-Agent System (Google ADK)

An autonomous multi-agent production system built with the **Google Agent Development Kit (ADK)** and powered by **Google Gemini**. The system coordinates a team of specialized AI agents—researchers, screenwriters, critics, casting directors, and box office analysts—to iteratively research, draft, critique, cast, and generate complete movie pitch and screenplay documents.

---

## Architecture & How It Works

The system implements multiple agent patterns (Sequential, Loop, and Parallel) wrapped into a unified workflow:

```mermaid
graph TD
    User([User Prompt]) --> Greeter[greeter Agent]
    Greeter --> FilmConcept[film_concept_team SequentialAgent]
    
    subgraph Writers Room [writers_room LoopAgent]
        Researcher[researcher Agent <br/> Wikipedia Search] --> Screenwriter[screenwriter Agent <br/> 3-Act Outline]
        Screenwriter --> Critic[critic Agent <br/> Feedback Loop / exit_loop]
        Critic -->|Iterate up to 5x| Researcher
    end

    FilmConcept --> Writers Room
    
    subgraph Preproduction [preproduction_team ParallelAgent]
        BoxOffice[box_office_researcher Agent <br/> Forecast & Comps]
        Casting[casting_agent Agent <br/> Actor Suggestions]
    end

    Writers Room --> Preproduction
    
    Preproduction --> FileWriter[file_writer Agent]
    FileWriter --> Output[movie_pitches/*.txt]
```

### Specialized Agents:
1. **`greeter`** *(Root Agent)*: Greets the user, collects the historical figure/theme prompt, and initiates the workflow.
2. **`writers_room`** *(LoopAgent)*:
   - **`researcher`**: Uses Wikipedia tools to gather factual historical context.
   - **`screenwriter`**: Drafts and refines the logline and 3-act plot outline.
   - **`critic`**: Reviews cinematic structure and historical fidelity. Exits the loop when satisfied or cycles back with constructive feedback (up to 5 iterations).
3. **`preproduction_team`** *(ParallelAgent)*:
   - **`box_office_researcher`**: Analyzes market potential and comparisons.
   - **`casting_agent`**: Suggests suitable actors for main characters based on critical reception.
4. **`file_writer`**: Compiles the final pitch package and writes it to disk in the `movie_pitches/` directory.

---

## Two Ways to Run

You can run this application in two modes without modifying any of the core agent code:
1. **Interactive Web UI (`adk web`)**: Best for local development and visual inspection of agent steps.
2. **Docker Container Microservice (`container_wrapper.py`)**: Best for production deployment, microservice architectures, and integration with an Agent Router.

---

### Mode 1: Run Using ADK Web (Local CLI)

#### 1. Setup Environment
Ensure your `.env` file in the project root contains your Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_GENAI_USE_VERTEXAI=False
MODEL=gemini-3.5-flash-lite
```

#### 2. Install Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r adk_multiagent_systems/requirements.txt
```

#### 3. Launch ADK Web
From inside the `adk_multiagent_systems/` directory:
```bash
cd adk_multiagent_systems
adk web
```
Open your browser at `http://localhost:8000` to interact with `workflow_agents` visually.

---

### Mode 2: Run in a Docker Container

The containerized version wraps `workflow_agents` inside [`container_wrapper.py`](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/class_7_buildMultiAgentSysADK/adk_multiagent_systems/container_wrapper.py), exposing a lightweight HTTP REST API (Flask + in-memory ADK session runner), complete with JWT authentication and router auto-registration.

#### Container Features:
- **Container Name**: `agent-movie-script`
- **Default Port**: `8010` (mapped to host `8010:8010`)
- **Docker Network**: `agent-movie-script` (bridge)
- **Persistent Storage**: The host directory `./movie_pitches` is volume-mounted to `/app/adk_multiagent_systems/movie_pitches` so pitch documents are immediately saved to your host machine.

#### 1. Start the Container
From the `adk_multiagent_systems/` directory:
```bash
cd adk_multiagent_systems

# Unset DOCKER_HOST if your shell has Podman socket redirection
unset DOCKER_HOST
docker compose up --build -d
```

#### 2. Check Container Status and Logs
```bash
docker ps | grep agent-movie-script
docker logs -f agent-movie-script
```

#### 3. Stop the Container
```bash
docker compose down
```

---

## How to Access and Use the Containerized Agent

### 1. Accessing from Host Machine (`localhost`)

#### A. Health Check Endpoint
```bash
curl http://localhost:8010/health
```
**Response:**
```json
{
  "port": 8010,
  "role": "Movie Script & Screenplay Creation Specialist",
  "service": "agent-movie-script",
  "status": "healthy"
}
```

#### B. Chat Endpoint (`POST /api/agent/chat`)
The chat endpoint requires JWT authentication. The token can be supplied via the `Authorization: Bearer <TOKEN>` header or directly in the JSON payload (`jwt_token`).

**Step 1: Generate a JWT Token**
Using the included [`jwt_auth.py`](file:///home/pi-net/Documents/agent_eng_labs/ai-agent-experiments/class_7_buildMultiAgentSysADK/adk_multiagent_systems/jwt_auth.py) helper:
```bash
cd adk_multiagent_systems
python3 -c "import jwt_auth; print(jwt_auth.generate_jwt_token('user@example.com'))"
```

**Step 2: Send a Request via `curl`**
```bash
TOKEN=$(python3 -c "import jwt_auth; print(jwt_auth.generate_jwt_token('user@example.com'))")

curl -X POST http://localhost:8010/api/agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "message": "Create a movie plot outline about Ada Lovelace and the analytical engine",
    "conversation_id": "session-101"
  }'
```

**Step 3: Call via Python `requests`**
```python
import requests
import jwt_auth

token = jwt_auth.generate_jwt_token("writer@studio.com")

response = requests.post(
    "http://localhost:8010/api/agent/chat",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "message": "Write a pitch about Marie Curie discovering radium",
        "conversation_id": "curie-pitch-1"
    }
)

print(response.json()["response"])
```

---

### 2. Accessing from Other Containers via Docker Gateway IP

When interacting with other containerized services (such as `agents-router`, web UI containers, or external microservices running on separate Docker networks), `localhost:8010` cannot be used inside the other container because `localhost` refers to the container itself.

Instead, other containers can reach `agent-movie-script` through the **Docker Gateway IP** of the host.

#### Why Use the Docker Gateway IP?
When `agent-movie-script` exposes port `8010:8010`, the host listens on `0.0.0.0:8010`. Containers on Docker bridge networks can route directly to the host using the bridge network's gateway IP address.

#### How to Find the Gateway IP:
1. **Default Docker Bridge Gateway**:
   ```bash
   docker network inspect bridge -f '{{range .IPAM.Config}}{{.Gateway}}{{end}}'
   # Usually: 172.17.0.1
   ```

2. **Specific Docker Network Gateway (e.g., `agent-with-rag_default`)**:
   ```bash
   docker network inspect agent-with-rag_default -f '{{range .IPAM.Config}}{{.Gateway}}{{end}}'
   # E.g.: 172.20.0.1
   ```

#### Access URL for Other Containers:
```
http://<DOCKER_GATEWAY_IP>:8010
```
*Examples:*
- `http://172.17.0.1:8010` (default bridge)
- `http://172.20.0.1:8010` (custom bridge)

#### Configuring in `manual_agents.json` / Agent Router:
If registering `agent-movie-script` in a router's manual agent configuration (e.g. `agent_router/data/manual_agents.json`):
```json
{
  "id": "agent-movie-script",
  "name": "Movie Script & Screenplay Specialist",
  "url": "http://172.17.0.1:8010",
  "health_url": "http://172.17.0.1:8010/health",
  "description": "Writes screenplays, film pitches, and plot outlines with casting and box office forecasts."
}
```
*(Replace `172.17.0.1` with the Gateway IP of the router container's network).*

---

## Configuration & Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini API Key | Required |
| `GOOGLE_GENAI_USE_VERTEXAI` | Use Gemini Developer API instead of Vertex AI | `False` |
| `MODEL` | Gemini Model identifier | `gemini-3.5-flash-lite` |
| `PORT` | HTTP server port for container wrapper | `8010` |
| `ROUTER_URL` | URL of the Agent Router for auto-registration | `http://agents_router:8004` |
| `JWT_SECRET` | Secret key used to sign and verify JWT tokens | `super-secret-jwt-agent-rag-key-2026` |

---

## File Structure

```text
class_7_buildMultiAgentSysADK/
├── README.md                  # Project documentation
├── .env                       # Environment variables (API keys)
├── .dockerignore              # Excludes virtual environments and local secrets
├── adk_utils/                 # Shared logging and 429 rate-limiting plugins
└── adk_multiagent_systems/
    ├── README.md              # Subdirectory documentation
    ├── Dockerfile             # Multi-stage image specification
    ├── docker-compose.yml     # Compose file (service, port, volumes, network)
    ├── container_wrapper.py   # Flask REST API + ADK Runner wrapper
    ├── jwt_auth.py            # JWT token validation & generation
    ├── requirements.txt       # Python dependencies
    ├── movie_pitches/         # Generated output documents (mounted to host)
    └── workflow_agents/
        └── agent.py           # Core Google ADK multi-agent workflow
```
