# Resilient AI — LLM Chat with Intelligent Failover & Response Caching

Resilient AI is a full-stack conversational application built with FastAPI, LiteLLM, SQLite, React, and Docker. It demonstrates a resilient LLM gateway featuring automatic multi-key failover, in-memory response caching, token usage tracking, and simulated provider fault injection.

---

## 1. Live URLs

- **Frontend**: https://resilient-one.vercel.app
- **Backend**: https://resilient-ai-gateway.onrender.com
- **Backend Health**: https://resilient-ai-gateway.onrender.com/health

> **Deployment Notes**:
> - **Hosting**: The live frontend is hosted on **Vercel**, and the live backend is hosted on **Render**.
> - **Storage**: The public Render deployment runs on Render's free web service tier, which uses ephemeral container filesystem storage (Render persistent disks require paid Starter instances). The repository's canonical Docker configuration specifies SQLite persistence at `/data/app.db` via a named Docker volume (`app_data`), which has been verified locally across container restarts and recreations.
> - **Cold Starts**: Render free-tier web services spin down after periods of inactivity. If the service is idle, the initial request may take 40–50 seconds to spin up before returning to standard low-latency responses.

---

## 2. Run locally: with Docker and without

### Environment Configuration

Before running locally, create your local `.env` file from the provided template:

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

Edit `.env` to configure your API keys and model:

```ini
LLM_API_KEYS=your_first_key,your_second_key
LLM_MODEL=gemini/gemini-3-flash-preview
DATABASE_URL=sqlite:///./app.db
ALLOWED_ORIGINS=http://localhost:3000
ENABLE_FAILURE_SIMULATION=true
CACHE_ENABLED=true
```

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `LLM_API_KEYS` | Comma-separated pool of provider API keys (mapped to `key_1`, `key_2`, etc.) | *Required* |
| `LLM_MODEL` | LiteLLM model identifier | `gemini/gemini-3-flash-preview` |
| `DATABASE_URL` | SQLite connection string (`sqlite:////data/app.db` in Docker) | `sqlite:///./app.db` |
| `ALLOWED_ORIGINS` | Permitted CORS origins for API requests | `http://localhost:3000` |
| `ENABLE_FAILURE_SIMULATION` | Enables testing via the `X-Simulate-Failure` header | `true` |
| `CACHE_ENABLED` | Enables LiteLLM built-in response caching | `true` |
| `VITE_API_BASE_URL` | (Frontend) Target backend base URL | `http://localhost:8000` |

---

### Option A: Running with Docker (Recommended)

Using Make:

```bash
# Build and start all services in the background
make up

# Stop all services cleanly (preserves SQLite named volume)
make down
```

Or using Docker Compose directly:

```bash
# Build and start containers
docker compose up --build -d

# Check service health and status
docker compose ps

# View live container logs
docker compose logs -f

# Stop containers
docker compose down
```

Once started:
- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option B: Running without Docker

#### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

#### 1. Backend Setup (Terminal 1)
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Start FastAPI with Uvicorn
make run-backend
# or: python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Setup (Terminal 2)
```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

#### 3. Run Test Suites
```bash
# Run all automated tests (backend pytest + frontend vitest)
make test

# Or run individually:
python -m pytest backend/tests -v
cd frontend && npm test
```

---

## 3. Design decisions: key fallback, caching, SQLite session storage

### Sequential Key Failover
- **Key Masking & Identity**: Real API keys provided in `LLM_API_KEYS` are loaded into an internal mapping and assigned safe identifiers (`key_1`, `key_2`, ...). Secret values are never logged, returned to clients, or committed.
- **Failover Trigger**: When an inference call fails with a fallback-eligible error (HTTP 429 rate limit, HTTP 500/502/503 provider errors, connection timeouts, or quota exhaustion), the gateway catches the exception, increments `fallback_attempts`, and transparently retries with the next configured key.
- **Exhaustion Contract**: If every key in the pool is exhausted or fails, the gateway returns `HTTP 503 Service Unavailable` with the exact payload:
  ```json
  {"detail": "all providers unavailable"}
  ```

### LiteLLM In-Memory Response Caching
- **Built-In Cache**: Configured directly through LiteLLM's official caching mechanism (`litellm.cache = Cache(type="local")`). Custom dictionary caches were avoided to adhere strictly to LiteLLM's hashing and TTL specifications.
- **Cache Hit Detection**: On a cache hit, LiteLLM resolves the turn locally with single-digit latency. The gateway detects cache hits via LiteLLM's `_hidden_params["cache_hit"]` flag, returning `resolution_source="LLM_CACHE"` and setting `key_id=null` (rendered as `Key: —`).
- **Cache Invalidation & Isolation**: Cache keys incorporate the active model, system prompt, and message history, preventing cross-session contamination.

### SQLite Session Storage & Atomic Persistence
- **Storage Architecture**: Built exclusively on SQLite using write-ahead logging (`PRAGMA journal_mode=WAL;`) for concurrent read/write operations and immediate crash recovery.
- **Multi-Turn Assembly**: For each request, the gateway pulls prior conversation turns for that `session_id` from SQLite (ordered chronologically `ORDER BY id ASC`), prepends the optional system prompt, appends the current user message, and forwards the full conversation to the model.
- **Atomic Transactions & Failure Isolation**: If a turn fails (e.g. all keys fail with HTTP 503), the failed user message and assistant reply are **not** persisted to SQLite. Querying a session that experienced only failed turns returns `HTTP 404 Not Found`, ensuring clean conversation histories.
- **Docker Volume Persistence**: In Docker, SQLite stores data at `/data/app.db`, mounted to the named volume `app_data`. The database and conversation histories persist across container restarts and recreations.

### Per-Request Token Tracking
- For every live inference call, the gateway captures usage data directly from the provider response (`usage.prompt_tokens` and `usage.completion_tokens`), exposing them as `input_tokens` and `output_tokens` in the metadata payload.

---

## 4. Verification: how to see failover, cache hits and per-message token usage

### 1. Response Caching Verification
LiteLLM response caching can be verified by submitting an identical first message across two distinct sessions:

```bash
# Turn 1: Fresh session (Live Inference)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "s-test-cache-1", "message": "What is the capital of Italy?"}'

# Observe response:
# "resolution_source": "LIVE_INFERENCE", "key_id": "key_1", "latency_ms": ~1400

# Turn 2: New session with identical message (Cache Hit)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "s-test-cache-2", "message": "What is the capital of Italy?"}'

# Observe response:
# "resolution_source": "LLM_CACHE", "key_id": null, "fallback_attempts": 0, "latency_ms": ~2
```
In the frontend UI, the green `[LLM_CACHE]` badge will illuminate with `Key: —` and near-zero latency.

---

### 2. Automatic Key Failover Verification
Simulate a rate limit (`429`) on `key_1` using the `X-Simulate-Failure` header:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-Simulate-Failure: key_1=429" \
  -d '{"session_id": "s-test-failover", "message": "Explain failover in one sentence."}'
```
**Expected Response**:
- HTTP 200 OK
- `metadata.resolution_source`: `"LIVE_INFERENCE"`
- `metadata.key_id`: `"key_2"`
- `metadata.fallback_attempts`: `1`

In the UI, the metadata footer will display `Key key_2 · 1 fallback`.

---

### 3. All Keys Exhausted (HTTP 503) Verification
Simulate a provider outage across all keys using wildcard simulation (`*=429`):

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-Simulate-Failure: *=429" \
  -d '{"session_id": "s-test-exhaust", "message": "This will fail."}'
```
**Expected Response**:
- HTTP 503 Service Unavailable
- Response Body: `{"detail": "all providers unavailable"}`

Verify failed turn is not saved:
```bash
curl -i http://localhost:8000/sessions/s-test-exhaust/messages
# Expected: HTTP 404 Not Found, {"detail": "session not found"}
```

---

### 4. Frontend Interactive Demo Controls
The web interface includes interactive demo controls anchored directly to the floating composer:
- Click **🧪 Demo Failure Simulation** to toggle between **Normal**, **Simulate key_1 (429)**, and **Simulate All Keys (429)**.
- Click **⚙️ System Prompt** to provide custom persona instructions (e.g., *"Answer in French"*).
- Every response visibly renders:
  - Source pill: `[LIVE_INFERENCE]` (blue) or `[LLM_CACHE]` (emerald)
  - Model and formatted latency (e.g. `1,280 ms`)
  - Token telemetry (`Input 24 · Output 68`)
  - Safe key identity (`Key key_1` or `Key —`)
  - Fallback attempt counter (`0 fallbacks` or `1 fallback`)

---

## 5. Setup Used: your editor and AI tools

- **Editor / Development Environment**: Antigravity IDE (Windows).
- **AI Assistance**: Antigravity coding agent and ChatGPT were used for implementation guidance, debugging test lifecycle issues, architectural review of LiteLLM caching behaviors, and verification.

---

## 6. Bonus features (if any): what you added beyond the requirements and why

1. **Collapsible System Prompt Drawer (`system-prompt-input`)**:
   - Allows users to inject persona and style constraints per conversation without saving the instructions as a user turn in SQLite.
2. **Interactive Failure Simulation Controls**:
   - Built directly into the floating composer so evaluators can trigger failovers and 503 errors directly in the browser without manually modifying headers in curl.
3. **Live Health & Configuration Indicator**:
   - A real-time status pill in the header showing backend connectivity, configured key count, and active cache state.
4. **Refined Conversational Widget UI**:
   - A floating, dark-surface chat interface inspired by compact modern widget design, featuring distinct blue user capsules, unbordered assistant responses, and quick-reply starter suggestions.
5. **Automated Frontend Test Suite (Vitest + Testing Library)**:
   - 10 component and integration tests asserting all required `data-testid` attributes, cache hit states, failover chips, and error notifications.
6. **Hardened Multi-Stage Docker Setup**:
   - Backend runs under an unprivileged user (`appuser`, UID 1001) with dedicated `/data` volume permissions, Docker health checks, and sequenced service startup.
