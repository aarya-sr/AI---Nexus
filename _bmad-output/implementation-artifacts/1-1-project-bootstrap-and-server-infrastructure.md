# Story 1.1: Project Bootstrap & Server Infrastructure

## Status: review

## Story

As a **developer**,
I want a running FastAPI server with WebSocket endpoints, session management, and typed message models,
So that the backend is ready to support the pipeline and frontend communication.

---

## Acceptance Criteria (ACs)

### AC1: Health Endpoint
- **Given** the backend server is started with `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **When** a client sends `GET /health`
- **Then** the server responds with HTTP 200 and body `{"status": "ok"}`

Implementation notes:
- This is the simplest possible liveness probe — no database ping, no dependency check
- Must respond under 50ms; no async I/O needed

---

### AC2: CORS Configuration
- **Given** CORS middleware is configured on the FastAPI app
- **When** the React frontend at `http://localhost:5173` makes any request (GET, POST, WebSocket upgrade)
- **Then** the request is not blocked by CORS policy

Implementation notes:
- Allow origins: `["http://localhost:5173", "http://127.0.0.1:5173"]`
- Allow methods: `["GET", "POST", "OPTIONS"]`
- Allow headers: `["*"]`
- Allow credentials: `True`
- Use `fastapi.middleware.cors.CORSMiddleware`

---

### AC3: Session Creation Endpoint
- **Given** the server is running
- **When** a client sends `POST /sessions` (no request body required)
- **Then** the server:
  1. Generates a UUID v4 string as the session ID
  2. Creates the directory `generated_agents/{session_id}/` relative to the backend working directory
  3. Registers the session in an in-memory session registry (dict keyed by session_id)
  4. Returns HTTP 201 with body `{"session_id": "<uuid>"}`

Implementation notes:
- The `generated_agents/` root directory must be created at startup if it does not exist
- Use `pathlib.Path` throughout, never string concatenation for paths
- Session registry lives in `session_service.py` as a module-level dict — not a database for this story
- Session creation timestamp must be stored alongside the session_id for future cleanup

---

### AC4: WebSocket Chat Channel
- **Given** a valid `session_id` exists in the registry
- **When** a client connects to `ws://localhost:8000/ws/chat/{session_id}`
- **Then**:
  1. The WebSocket connection is accepted
  2. The server immediately sends a `chat.message` welcome message (see message format below)
  3. The connection remains open and the server can push subsequent messages

- **Given** an invalid or unknown `session_id`
- **When** a client connects to `ws://localhost:8000/ws/chat/{session_id}`
- **Then** the connection is closed with code 4004 and a reason string `"unknown session"`

Implementation notes:
- Use `fastapi.WebSocket` and `fastapi.WebSocketDisconnect`
- Store the active WebSocket in the session registry under `"chat_ws"` key so other services can push to it later
- On `WebSocketDisconnect`, remove the connection reference from registry but keep the session alive
- The welcome `chat.message` payload: `{"text": "Frankenstein is ready. Describe the agent you want to build."}`

---

### AC5: WebSocket Status Channel
- **Given** a valid `session_id` exists in the registry
- **When** a client connects to `ws://localhost:8000/ws/status/{session_id}`
- **Then**:
  1. The WebSocket connection is accepted
  2. The server immediately sends a `status.stage_update` message with the current pipeline stage (`"idle"`)
  3. The connection remains open

- **Given** an invalid `session_id`
- **When** a client connects to `ws://localhost:8000/ws/status/{session_id}`
- **Then** the connection is closed with code 4004

Implementation notes:
- Same WebSocket lifecycle pattern as AC4
- Store under `"status_ws"` key in the session registry
- Initial `status.stage_update` payload: `{"stage": "idle", "description": "Waiting for prompt"}`
- This channel is write-only from the server perspective — the client only listens here
- The server will push updates through this channel as the pipeline advances (future stories)

---

### AC6: WebSocket Message Models (`messages.py`)
- **Given** `app/models/messages.py` is imported
- **When** any message type is instantiated
- **Then** the model validates, serializes to JSON with dot-notation `type` field, ISO-8601 `timestamp`, and `session_id`

All eight message types must be importable and usable:

| Class Name | `type` value | When used |
|---|---|---|
| `ChatMessage` | `chat.message` | Server sends text to user |
| `QuestionGroupMessage` | `chat.question_group` | Elicitor pushes Q&A batch |
| `CheckpointMessage` | `chat.checkpoint` | Human approval request |
| `StageUpdateMessage` | `status.stage_update` | Pipeline stage changes |
| `ProgressMessage` | `status.progress` | Within-stage progress % |
| `CompleteMessage` | `status.complete` | Build finished |
| `ErrorMessage` | `error.llm_failure` or `error.pipeline_failure` | Error conditions |
| `ControlMessage` | `control.approve`, `control.reject`, `control.user_input` | Client → Server control signals |

Implementation notes:
- Base class handles `timestamp` (auto-set to `datetime.utcnow().isoformat() + "Z"`) and `session_id`
- `type` is a `Literal` field on each subclass — never a free-form string
- `payload` is a `dict` — typed dicts or inline dicts are both acceptable for now
- `model_dump(mode="json")` must produce valid JSON with no non-serializable types
- `ControlMessage` is the only message type sent from client to server; all others are server → client

---

### AC7: Session Service (`session_service.py`)
- **Given** `app/services/session_service.py` is imported
- **When** `SessionService.create_session()` is called
- **Then** a UUID v4 is generated, a session record is stored in the in-memory registry, and the `generated_agents/{session_id}/` directory is created

- **When** `SessionService.get_session(session_id)` is called with a valid ID
- **Then** the session record dict is returned

- **When** `SessionService.get_session(session_id)` is called with an unknown ID
- **Then** `None` is returned

- **When** `SessionService.cleanup_old_sessions(max_age_hours=24)` is called at server startup
- **Then** any `generated_agents/*/` directories older than `max_age_hours` are deleted

Implementation notes:
- Session record schema (in-memory dict):
  ```python
  {
      "session_id": str,          # UUID v4
      "created_at": datetime,     # datetime.utcnow()
      "stage": str,               # current pipeline stage, starts as "idle"
      "chat_ws": WebSocket | None,
      "status_ws": WebSocket | None,
  }
  ```
- `cleanup_old_sessions` uses `pathlib.Path.stat().st_mtime` on the session directory to determine age
- Call `cleanup_old_sessions` once inside a FastAPI `lifespan` startup handler, not via a background task
- The session registry is a module-level `dict[str, dict]` — thread safety is acceptable via GIL for hackathon scope

---

### AC8: Config Extended for Session Management
- **Given** `app/config.py` already defines `Settings` with `pydantic-settings`
- **When** `settings` is imported
- **Then** the following additional fields are available:
  - `chroma_persist_dir: str` — default `"./chroma_data"`, from env `CHROMA_PERSIST_DIR`
  - `generated_agents_dir: str` — default `"./generated_agents"`, from env `GENERATED_AGENTS_DIR`
  - `session_max_age_hours: int` — default `24`, from env `SESSION_MAX_AGE_HOURS`
  - `backend_host: str` — default `"0.0.0.0"`, from env `BACKEND_HOST`
  - `backend_port: int` — default `8000`, from env `BACKEND_PORT`

---

## Technical Implementation Notes

### Architecture

This story creates the following files. Files that already partially exist are marked.

```
backend/
├── app/
│   ├── main.py                     # CREATE — FastAPI app entrypoint
│   ├── config.py                   # EXTEND — add 5 new fields (file exists)
│   ├── models/
│   │   ├── messages.py             # CREATE — WebSocket message types
│   │   └── [other models exist]    # DO NOT TOUCH in this story
│   └── services/
│       ├── session_service.py      # CREATE — session lifecycle manager
│       └── [chroma_service.py,     # DO NOT TOUCH in this story
│            llm_service.py exist]
```

Dependency direction for files created in this story:
```
config.py
    ↑
messages.py   (no deps on services or other models)
    ↑
session_service.py  (imports config, messages)
    ↑
main.py  (imports config, session_service, messages)
```

Do NOT import from `pipeline/`, `agents/`, or `chroma_service` in this story. Those are wired up in later stories.

---

### Data Models

#### `app/models/messages.py` — Full field definitions

```python
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    type: str                          # overridden by each subclass as Literal
    payload: dict[str, Any] = {}
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    session_id: str = ""


class ChatMessage(BaseMessage):
    type: Literal["chat.message"] = "chat.message"
    # payload keys: {"text": str}


class QuestionGroupMessage(BaseMessage):
    type: Literal["chat.question_group"] = "chat.question_group"
    # payload keys: {
    #   "round": int,                  # which Q&A round (1-3)
    #   "questions": list[dict],       # [{id: str, category: str, text: str}]
    # }


class CheckpointMessage(BaseMessage):
    type: Literal["chat.checkpoint"] = "chat.checkpoint"
    # payload keys: {
    #   "checkpoint": str,             # "requirements" | "spec"
    #   "data": dict,                  # the RequirementsDoc or AgentSpec serialized
    #   "critique": dict | None,       # CritiqueReport serialized (spec checkpoint only)
    # }


class StageUpdateMessage(BaseMessage):
    type: Literal["status.stage_update"] = "status.stage_update"
    # payload keys: {"stage": str, "description": str}


class ProgressMessage(BaseMessage):
    type: Literal["status.progress"] = "status.progress"
    # payload keys: {"stage": str, "percent": int, "detail": str}


class CompleteMessage(BaseMessage):
    type: Literal["status.complete"] = "status.complete"
    # payload keys: {
    #   "session_id": str,
    #   "framework": str,              # "crewai" | "langgraph"
    #   "download_url": str,           # "/sessions/{id}/download"
    #   "summary": str,
    # }


class ErrorMessage(BaseMessage):
    type: Literal["error.llm_failure", "error.pipeline_failure"]
    # payload keys: {"stage": str, "message": str, "recoverable": bool}


class ControlMessage(BaseMessage):
    type: Literal["control.approve", "control.reject", "control.user_input"]
    # payload keys vary:
    #   control.approve:     {"checkpoint": str}
    #   control.reject:      {"checkpoint": str, "feedback": str}
    #   control.user_input:  {"round": int, "answers": list[dict]}
    #                        answers = [{question_id: str, answer: str}]
```

Note: `ErrorMessage` has a `type` field that accepts a `Literal` union. Pydantic v2 handles this correctly via `Literal["error.llm_failure", "error.pipeline_failure"]`.

---

#### `app/services/session_service.py` — Session record shape

```python
# In-memory registry entry (not a Pydantic model — just a dict for simplicity)
session_record = {
    "session_id": str,          # UUID v4 string
    "created_at": datetime,     # datetime.utcnow(), used for cleanup age check
    "stage": str,               # pipeline stage; starts as "idle"
    "chat_ws": WebSocket | None,    # active WS connection or None
    "status_ws": WebSocket | None,  # active WS connection or None
}
```

Public interface of `SessionService`:

```python
class SessionService:
    def create_session(self) -> str:
        """Create session, create directory, register. Returns session_id."""

    def get_session(self, session_id: str) -> dict | None:
        """Return session record or None if unknown."""

    def session_exists(self, session_id: str) -> bool:
        """True if session_id is registered."""

    def set_chat_ws(self, session_id: str, ws: WebSocket) -> None:
        """Attach/replace the chat WebSocket on a session."""

    def clear_chat_ws(self, session_id: str) -> None:
        """Remove chat WebSocket reference (called on disconnect)."""

    def set_status_ws(self, session_id: str, ws: WebSocket) -> None:
        """Attach/replace the status WebSocket on a session."""

    def clear_status_ws(self, session_id: str) -> None:
        """Remove status WebSocket reference (called on disconnect)."""

    def update_stage(self, session_id: str, stage: str) -> None:
        """Update the current pipeline stage for a session."""

    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """Delete generated_agents dirs older than max_age_hours. Returns count deleted."""

    def get_session_dir(self, session_id: str) -> Path:
        """Return Path to generated_agents/{session_id}/."""
```

---

### API Endpoints

All endpoints live in `app/main.py`. No routers/blueprints needed for this story — direct registration on the app.

#### `GET /health`
```
Response 200: {"status": "ok"}
```

#### `POST /sessions`
```
Request body: none
Response 201: {"session_id": "<uuid-v4>"}
Response 500: {"detail": "Failed to create session directory"}
```

#### `WebSocket /ws/chat/{session_id}`
```
On connect:
  - Validate session_id exists → close(4004) if not
  - Accept connection
  - Register WS on session via session_service.set_chat_ws()
  - Send ChatMessage welcome

On message received from client:
  - Parse as ControlMessage
  - For this story: echo back an ErrorMessage("not yet implemented") — pipeline not wired
  - In Story 1.3: this dispatches to the Elicitor

On disconnect:
  - session_service.clear_chat_ws(session_id)
  - Log at INFO level

Close codes used:
  - 4004: unknown session_id
  - 1000: normal closure
```

#### `WebSocket /ws/status/{session_id}`
```
On connect:
  - Validate session_id → close(4004) if not
  - Accept connection
  - Register WS via session_service.set_status_ws()
  - Send StageUpdateMessage(stage="idle", description="Waiting for prompt")

On disconnect:
  - session_service.clear_status_ws(session_id)
  - Log at INFO level

Note: No inbound messages expected on this channel.
      If client sends anything, silently ignore.
```

#### Helper function in `main.py`

```python
async def send_message(ws: WebSocket, msg: BaseMessage) -> None:
    """Serialize a message model and send over WebSocket. Swallows send errors."""
```

This function will be used by future agents/pipeline nodes to push updates. Keep it as a standalone async function, not a method, so it can be imported elsewhere.

---

### Key Technical Decisions

1. **Single-process, in-memory session registry.** No Redis, no database. The session dict is module-level in `session_service.py`. This is acceptable for the hackathon — one uvicorn worker, no horizontal scaling needed. If this assumption changes, the `SessionService` class boundary makes it easy to swap the backing store.

2. **No session persistence across restarts.** Sessions are ephemeral. On server restart, old in-memory sessions are gone. The `generated_agents/` directories on disk persist and are cleaned up at startup by `cleanup_old_sessions`.

3. **WebSocket connections stored directly in session record.** FastAPI `WebSocket` objects are not serializable. They live only in memory. This means if uvicorn restarts, all WebSocket connections are severed — clients must reconnect. The frontend should implement reconnect logic (Story 1.2).

4. **`lifespan` context manager over `on_event` deprecated handlers.** Use the modern FastAPI pattern:
   ```python
   from contextlib import asynccontextmanager

   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # startup
       session_service.cleanup_old_sessions()
       Path(settings.generated_agents_dir).mkdir(parents=True, exist_ok=True)
       yield
       # shutdown (nothing needed for now)

   app = FastAPI(lifespan=lifespan)
   ```

5. **Logging configuration in `main.py`.** Configure Python stdlib logging at startup, not per-file. All modules use `logger = logging.getLogger(__name__)`. Never `print()`.
   ```python
   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
   )
   ```

6. **`POST /sessions` returns 201, not 200.** Use `JSONResponse(content=..., status_code=201)` or declare `status_code=201` on the route decorator.

7. **WebSocket close code 4004 for unknown sessions.** Code 4000-4999 are reserved for application use. 4004 = "not found" by convention. Use `await websocket.close(code=4004, reason="unknown session")` before returning from the handler. Never raise an exception — that produces a 500 instead of a clean close.

8. **`messages.py` is in `app/models/`, not `app/services/`.** It is a data definition, not a service. It has no imports from services or agents.

9. **`ErrorMessage` type union.** Pydantic v2 supports `Literal["a", "b"]` for a field that accepts either value. Set the default to `"error.pipeline_failure"` so instantiation without specifying type works for the generic error case.

10. **`generated_agents_dir` is configurable via env.** Do not hardcode `"./generated_agents"` in `session_service.py`. Import `settings.generated_agents_dir` from `config.py` so it can be overridden in Docker Compose (future story).

---

### Dependencies

All should be present or added to `backend/requirements.txt`:

```
# Already in requirements.txt (do not re-add):
pydantic>=2.0.0
pydantic-settings>=2.0.0
chromadb>=0.5.0
jinja2>=3.1.0
openai>=1.0.0

# Must ADD to requirements.txt:
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
websockets>=12.0          # uvicorn[standard] includes this, listed explicitly for clarity
python-multipart>=0.0.9   # needed by FastAPI for form data (upload in later stories)
```

Install with:
```bash
cd backend
python -m venv .venv        # if not already created
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Dev Notes

### Running the server

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

`--reload` watches for file changes. Do not use `--reload` in Docker.

### `.env` file

The server reads from `backend/.env` (not project root). Create it:

```bash
# backend/.env
OPENROUTER_API_KEY=sk-or-...
CHROMA_PERSIST_DIR=./chroma_data
GENERATED_AGENTS_DIR=./generated_agents
SESSION_MAX_AGE_HOURS=24
```

`pydantic-settings` will load this automatically because `config.py` already sets `model_config = {"env_file": ".env"}`.

### Testing the endpoints manually

```bash
# Health
curl http://localhost:8000/health

# Create session
curl -X POST http://localhost:8000/sessions

# WebSocket (requires wscat: npm i -g wscat)
wscat -c ws://localhost:8000/ws/chat/<session-id>
wscat -c ws://localhost:8000/ws/status/<session-id>
```

### Absolute imports

All imports must use absolute paths from `app`:
```python
from app.config import settings
from app.models.messages import ChatMessage, StageUpdateMessage
from app.services.session_service import SessionService
```

Never use relative imports (`from .config import ...`). This is a project-wide convention.

### `__init__.py` for new modules

`app/models/messages.py` does NOT need to be exported from `app/models/__init__.py` in this story. The `__init__.py` in models handles the pipeline data models (state, spec, etc.). Messages are a separate concern — import directly from `app.models.messages`.

### Pitfall: WebSocket close before accept

You cannot call `await websocket.close(code=4004)` before calling `await websocket.accept()` in some FastAPI versions. The safe pattern:

```python
await websocket.accept()
if not session_service.session_exists(session_id):
    await websocket.close(code=4004, reason="unknown session")
    return
```

Always accept first, then close if invalid.

### Pitfall: `datetime.utcnow()` deprecation

Python 3.12+ deprecates `datetime.utcnow()`. For hackathon scope this is fine — we are on Python 3.11 (see `backend/.venv/lib/python3.11/`). Do not add timezone handling complexity now.

### Pitfall: `generated_agents/` path resolution

`settings.generated_agents_dir` defaults to `"./generated_agents"`. This resolves relative to the **working directory where uvicorn is launched**, not relative to `main.py`. Always launch uvicorn from `backend/`:
```bash
cd backend && uvicorn app.main:app ...
```

If you launch from the project root, the path resolves to `frankenstein/generated_agents/` which is also fine, but be consistent.

### What this story does NOT include

- No `GET /sessions/{id}/download` — that is Story 3.5
- No `POST /sessions/{id}/approve` — that is Story 1.4
- No pipeline wiring — WebSocket messages from clients get a stub "not implemented" response
- No authentication or API keys on endpoints — out of scope for hackathon
- No Docker setup — that is Story 3.1/3.2
- No frontend — that is Story 1.2
- No tests beyond manual curl/wscat — automated tests are added per-story as the pipeline builds up

### Existing files to be aware of (do not regress)

The following files already exist and are correct. This story should not modify their core logic:

- `/Users/vedpawar2254/Desktop/personalP/frankenstein/backend/app/config.py` — extend only, add 5 fields
- `/Users/vedpawar2254/Desktop/personalP/frankenstein/backend/app/models/__init__.py` — do not modify
- `/Users/vedpawar2254/Desktop/personalP/frankenstein/backend/app/models/state.py` — do not modify
- `/Users/vedpawar2254/Desktop/personalP/frankenstein/backend/app/models/requirements.py` — do not modify
- `/Users/vedpawar2254/Desktop/personalP/frankenstein/backend/app/models/spec.py` — do not modify
- `/Users/vedpawar2254/Desktop/personalP/frankenstein/backend/app/models/critique.py` — do not modify
- `/Users/vedpawar2254/Desktop/personalP/frankenstein/backend/app/models/testing.py` — do not modify
- `/Users/vedpawar2254/Desktop/personalP/frankenstein/backend/app/models/learning.py` — do not modify
- `/Users/vedpawar2254/Desktop/personalP/frankenstein/backend/app/models/tools.py` — do not modify
- `/Users/vedpawar2254/Desktop/personalP/frankenstein/backend/app/models/code.py` — do not modify
- `/Users/vedpawar2254/Desktop/personalP/frankenstein/backend/app/services/llm_service.py` — do not modify
- `/Users/vedpawar2254/Desktop/personalP/frankenstein/backend/app/services/chroma_service.py` — do not modify

### Completion checklist

Before marking this story done:
- [ ] `curl http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] `curl -X POST http://localhost:8000/sessions` returns `{"session_id": "..."}` and creates directory in `generated_agents/`
- [ ] `wscat -c ws://localhost:8000/ws/chat/<id>` receives a `chat.message` welcome JSON
- [ ] `wscat -c ws://localhost:8000/ws/status/<id>` receives a `status.stage_update` JSON with `stage: "idle"`
- [ ] Connecting with an unknown session_id closes with code 4004
- [ ] Server starts cleanly with no import errors after adding fastapi/uvicorn to requirements
- [ ] `python -c "from app.models.messages import ChatMessage, QuestionGroupMessage, CheckpointMessage, StageUpdateMessage, ProgressMessage, CompleteMessage, ErrorMessage, ControlMessage; print('OK')"` succeeds
- [ ] No `print()` statements anywhere; only `logging`
- [ ] `config.py` has all 5 new fields and they load from `.env`

---

## References

- FR55-57 (pre-built): Server scaffold, REST API, WebSocket channels
- FR63: Session UUID management
- FR66: CORS for frontend at port 5173
- FR67: Session directory creation
- NFR3: Response time (health < 50ms)
- NFR8: Structured logging
- NFR11-14: API contracts
- NFR16-17: Session cleanup, graceful startup
- Solution Approach §6.2 (Full Stack), §3.1 (Pipeline State Object)
- HANDOFF.md §Layer 1 (Foundation)
