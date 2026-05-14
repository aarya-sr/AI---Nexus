---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-05-14'
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
  - docs/Frankenstein_Solution_Approach.md
  - docs/Frankenstein_Justification_Document.md
  - docs/Frankenstein_Product_Description.md
  - docs/HANDOFF.md
workflowType: 'architecture'
project_name: 'frankenstein'
user_name: 'ved'
date: '2026-05-14'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
64 FRs across 10 capability areas: Requirements Elicitation (FR1-9), Architecture & Specification (FR10-19), Adversarial Review (FR20-26), Spec Review & Approval (FR27-30), Code Generation (FR31-36), Testing & Validation (FR37-45), Learning & Memory (FR46-49), Tool Schema Library (FR50-54), LLM Service (FR55-58), Frontend Experience (FR59-64).

Architecturally, these decompose into:
- **Pipeline orchestration layer** — StateGraph definition, routing logic, state management, checkpoint pause/resume (FR24-25, FR43-44, FR7-8, FR27-30)
- **Agent execution layer** — 6 agents, each with distinct LLM model, structured I/O contracts, and domain-specific logic (FR2-6, FR10-19, FR20-23, FR31-36, FR37-42, FR46-48)
- **RAG/memory layer** — Chroma collections, embedding, query, write-back (FR10, FR47-49, FR50-54)
- **Code generation layer** — Template-driven compilation, two framework compilers (CrewAI, LangGraph), validation (FR31-36)
- **Execution/testing layer** — Process isolation, timeout, stdout/stderr capture, failure tracing (FR37-45)
- **Frontend/communication layer** — WebSocket chat, pipeline status streaming, spec rendering, file download (FR59-64)

**Non-Functional Requirements:**
- Performance: <10 min end-to-end, <500ms WebSocket, <60s per LLM call timeout
- Security: API keys server-side only, injected via config.yaml in generated output
- Integration: OpenRouter for all LLM calls, Chroma embedded, pip-only dependencies in generated code

**Scale & Complexity:**
- Primary domain: Full-stack AI pipeline orchestration
- Complexity level: Medium-high
- Estimated architectural components: 6 (pipeline engine, agent layer, RAG/memory service, code generator, execution sandbox, frontend)

### Technical Constraints & Dependencies

- LangGraph StateGraph as pipeline framework (pre-decided)
- OpenRouter as sole LLM gateway (pre-decided)
- Chroma as vector DB, embedded mode (pre-decided)
- FastAPI backend, React frontend (pre-decided)
- Docker execution post-MVP — MVP uses local subprocess
- Generated agents must be self-contained Python projects (pip install + python main.py)
- Two framework compilers needed: CrewAI and LangGraph output targets
- Cross-model adversarial review: Architect (Claude) and Critic (GPT-4o) must use different model families

### Cross-Cutting Concerns Identified

1. **State serialization & checkpoint resume** — Pipeline state must serialize for WebSocket transmission at checkpoints and resume on approval. Affects pipeline engine + frontend.
2. **LLM call management** — Retry with backoff, timeout, structured output parsing. Every agent uses LLM calls. Centralized LLM service needed.
3. **Error propagation across feedback loops** — Critic findings route back to Architect; Tester failures route to Builder or Architect. Error context must carry through state cleanly.
4. **Real-time status streaming** — Frontend needs live pipeline stage updates. WebSocket must carry both chat messages AND pipeline status events.
5. **Tool schema consistency** — Tool definitions used by Architect for selection, Builder for code templates, and Tester for validation. Single source of truth needed.

### UX Architectural Implications

- Single-column chat thread with inline rich content (agent cards, flow diagrams, critique badges) — frontend must render multiple component types within one scrollable thread
- Pipeline sidebar (240px fixed) with real-time stage indicators — separate WebSocket event stream or multiplexed on same connection
- Dark-mode-first with shadcn/ui + Tailwind CSS — component library pre-decided
- Desktop-only, min 1024px width — no responsive complexity
- Input disabled during autonomous pipeline phases, re-enabled at checkpoints

## Starter Template Evaluation

### Primary Technology Domain

Full-stack AI pipeline orchestration — Python backend + React frontend. Stack fully pre-decided in architecture docs.

### Starter Options Considered

**No external starter template applicable.** Frankenstein is a custom multi-component system (FastAPI + LangGraph pipeline + React frontend + Chroma). No existing starter covers this combination. Project scaffold defined in HANDOFF.md — used as the starter blueprint.

### Selected Approach: Custom Scaffold from HANDOFF.md

**Rationale:** Stack decisions already locked in Solution Approach and HANDOFF docs. External starters would introduce unwanted dependencies or patterns. The HANDOFF.md scaffold is purpose-built for this system.

**Initialization:**

```bash
# Backend
mkdir -p backend/app/{models,agents,pipeline,services,tool_library} backend/tests
pip install fastapi uvicorn langgraph langchain-core chromadb pydantic litellm

# Frontend
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
```

**Architectural Decisions (Pre-Decided):**

**Language & Runtime:**
- Backend: Python 3.11
- Frontend: TypeScript (React)

**Styling Solution:**
- Tailwind CSS + shadcn/ui (per UX spec)
- Dark-mode-first, Geist Sans font

**Build Tooling:**
- Backend: uvicorn (dev), no build step needed
- Frontend: Vite (fast HMR, React plugin)

**Testing Framework:**
- Backend: pytest
- Frontend: vitest

**Package Management:**
- Backend: pip + requirements.txt (venv)
- Frontend: npm

**Code Organization:**
- Backend follows HANDOFF.md scaffold: `app/` with `models/`, `agents/`, `pipeline/`, `services/`, `tool_library/`
- Frontend: `src/components/` (one file per custom component per UX spec)

**Development Experience:**
- Vite HMR for frontend
- uvicorn --reload for backend
- Local execution only (no cloud deployment for hackathon)

**Note:** Project initialization should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
All critical decisions pre-decided in Solution Approach + HANDOFF.md. Remaining decisions below are important but non-blocking.

**Important Decisions (Shape Architecture):**
- WebSocket protocol design
- Session management
- Frontend state management
- Error handling strategy
- Generated agent storage

**Deferred Decisions (Post-MVP):**
- Pipeline state persistence (SQLite checkpoint for production)
- Authentication and authorization
- Cloud deployment strategy
- Multi-tenancy
- Rate limiting

### Data Architecture

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Pipeline state persistence | In-memory only | Hackathon scope — no need to survive restarts. LangGraph `SqliteSaver` available as upgrade path |
| Vector DB | Chroma embedded | Pre-decided. No separate server, embedded in FastAPI process |
| Chroma collections | 4: tool_schemas, spec_patterns, anti_patterns, domain_insights | Pre-decided in Solution Approach §5.1 |
| Generated agent storage | Named directory per session (`generated_agents/{session_id}/`) | Allows re-download. Cleaned up periodically or on server restart |
| Data validation | Pydantic models throughout | Pre-decided. All pipeline state objects, LLM outputs, and API payloads use Pydantic |

### Authentication & Security

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Authentication | None | Hackathon demo — no user accounts |
| API key management | Server-side only, env var | OpenRouter key never exposed to frontend |
| Generated agent API keys | Injected via config.yaml at build time | Per FR58 |
| Execution isolation | Local subprocess with timeout (60s) | MVP. Docker post-MVP |

### API & Communication Patterns

| Decision | Choice | Rationale |
|----------|--------|-----------|
| WebSocket protocol | Separate endpoints: `/ws/chat/{session_id}` for conversation, `/ws/status/{session_id}` for pipeline events | Clean separation of concerns. Chat endpoint handles Elicitor Q&A + checkpoint approvals. Status endpoint streams stage transitions + progress |
| Session management | UUID generated per session, passed as query param on WS connect | Simple, stateless. No auth needed. UUID in URL path for both WS endpoints |
| REST endpoints | POST `/sessions` (create), GET `/sessions/{id}/download` (zip), POST `/sessions/{id}/approve` (checkpoint) | REST for non-streaming operations |
| Message format | Type-tagged JSON on each WS: `{type: string, payload: object, timestamp: string}` | Even with separate endpoints, type tags keep parsing clean |
| Error responses | Structured: `{type: "error", payload: {stage: string, message: string, recoverable: bool}}` | Frontend shows user-friendly message, hides technical detail |

### Frontend Architecture

| Decision | Choice | Rationale |
|----------|--------|-----------|
| State management | React context + useReducer | No external deps. WebSocket events dispatch to reducer. Simple for single-page conversation flow |
| Component library | shadcn/ui + custom components | Pre-decided in UX spec. 10 shadcn components + 11 custom components |
| Routing | None — single page | Conversation IS the interface. No page navigation |
| Flow diagram rendering | Custom flex layout with styled nodes | Per UX spec. No heavy graph library needed for simple directed flow |
| Spec rendering | Inline cards in chat thread | Agent cards, critique badges, flow diagram all render within conversation scroll |

### Infrastructure & Deployment

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Hosting | Local only | Hackathon. `uvicorn` for backend, `vite dev` for frontend |
| Process management | Single FastAPI process | Chroma embedded, LangGraph in-process. No microservices |
| Logging | Python `logging` to stdout | Simple. No log aggregation for hackathon |
| Environment config | `.env` file loaded by pydantic-settings | OpenRouter API key, model mappings, max iterations |

### Error Handling Strategy

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM failures | Centralized retry in LLM service (exponential backoff, 3 retries) | Per FR56 |
| Pipeline stage failures | Each agent wrapped in try/catch. Failures caught by pipeline, formatted as user-friendly messages, streamed via status WS | User never sees raw errors per UX spec |
| Partial success | Pipeline continues to Learner with partial success flag. Frontend shows amber completion card | Per FR45 |
| Feedback loop errors | Iteration counters prevent infinite loops. Max iterations → proceed with best result + warnings | Per FR25, FR44 |

### Decision Impact Analysis

**Implementation Sequence:**
1. Pydantic models (data foundation — everything depends on these)
2. LLM service (every agent needs this)
3. Chroma service (Architect needs RAG)
4. Pipeline graph + routing (orchestration spine)
5. Individual agents (Elicitor first, Architect second)
6. FastAPI endpoints + WebSocket handlers
7. React frontend + WebSocket client
8. Tool Schema Library seeding
9. Integration testing

**Cross-Component Dependencies:**
- WebSocket message types must match between FastAPI handlers and React reducer
- Pydantic models shared between agents, pipeline state, and API responses
- LLM service consumed by all 6 agents — interface must be stable before agents are built
- Chroma service consumed by Architect + Learner — collection schemas must be agreed before either is built
- Tool Schema Library must be seeded before Architect or Tester can function

## Implementation Patterns & Consistency Rules

### Critical Conflict Points Identified

12 areas where AI agents could make different choices, grouped into 5 categories.

### Naming Patterns

**Python Backend (PEP 8 strict):**
- Modules: `snake_case.py` — `llm_service.py`, `chroma_service.py`
- Classes: `PascalCase` — `FrankensteinState`, `CritiqueReport`
- Functions: `snake_case` — `route_after_critique()`, `find_similar_specs()`
- Variables: `snake_case` — `spec_iteration`, `build_outcome`
- Constants: `UPPER_SNAKE` — `MAX_SPEC_ITERATIONS`, `DEFAULT_TIMEOUT`

**Frontend TypeScript:**
- Component files: `PascalCase.tsx` — `ChatMessage.tsx`, `PipelineSidebar.tsx`
- Hooks: `camelCase.ts` with `use` prefix — `useWebSocket.ts`, `usePipelineState.ts`
- Utils: `camelCase.ts` — `formatMessage.ts`
- Types/interfaces: `PascalCase` — `ChatMessage`, `PipelineStage`
- Variables/functions: `camelCase` — `sessionId`, `handleApprove()`
- CSS classes: Tailwind only — no custom CSS files

**WebSocket Message Types (dot notation):**
- Chat: `chat.message`, `chat.question_group`, `chat.checkpoint`
- Status: `status.stage_update`, `status.progress`, `status.complete`
- Error: `error.llm_failure`, `error.pipeline_failure`
- Control: `control.approve`, `control.reject`, `control.user_input`

**Pipeline State Fields:**
- All fields `snake_case` — matches Pydantic convention
- Boolean fields prefixed: `requirements_approved`, `spec_approved`
- List fields pluralized: `elicitor_questions`, `failure_traces`
- Iteration counters: `spec_iteration`, `build_iteration`

**Generated Code (Builder output):**
- Follows target framework conventions, NOT Frankenstein conventions
- CrewAI output: CrewAI naming patterns (Agent, Tool, Crew classes)
- LangGraph output: LangGraph patterns (StateGraph, node functions)
- Builder templates enforce this — not left to LLM discretion

### Structure Patterns

**Backend Organization:**
```
backend/app/
├── models/          # Pydantic models ONLY — no business logic
├── agents/          # One file per pipeline agent — elicitor.py, architect.py, etc.
├── pipeline/        # Graph definition + routing logic ONLY
├── services/        # Shared services — llm, chroma, docker
├── tool_library/    # JSON tool schema files
└── main.py          # FastAPI app + endpoint definitions
```

**Rules:**
- Models never import from agents or services
- Agents import from models and services only
- Pipeline imports from agents only
- Services are stateless — no pipeline awareness
- No circular imports — dependency flows: models ← services ← agents ← pipeline ← main

**Frontend Organization:**
```
frontend/src/
├── components/      # One file per component (PascalCase.tsx)
├── hooks/           # Custom hooks (useX.ts)
├── context/         # React context + reducer
├── types/           # Shared TypeScript types
├── utils/           # Pure utility functions
└── App.tsx          # Root component
```

**Rules:**
- Components are self-contained — no component imports another component's internals
- All shared state goes through context, not prop drilling past 2 levels
- WebSocket connection managed in a single hook (`useWebSocket`)
- Types shared between components live in `types/`, not duplicated

**Test Organization:**
- Backend: `backend/tests/` mirroring `app/` structure — `tests/test_elicitor.py`, `tests/test_llm_service.py`
- Frontend: co-located — `ChatMessage.test.tsx` next to `ChatMessage.tsx`

### Format Patterns

**API Response Format:**
```json
{
  "type": "chat.message",
  "payload": { ... },
  "timestamp": "2026-05-14T10:30:00Z",
  "session_id": "uuid"
}
```
- Always type-tagged JSON
- Timestamps: ISO 8601 UTC
- IDs: UUID v4 strings
- No nested wrappers — `payload` is the content, flat structure

**Error Format (streamed via WebSocket):**
```json
{
  "type": "error.pipeline_failure",
  "payload": {
    "stage": "architect",
    "message": "Designing your agent architecture is taking longer than expected...",
    "recoverable": true
  },
  "timestamp": "..."
}
```
- `message` is always user-friendly (per UX spec)
- `recoverable` tells frontend whether to show retry or failure state
- Raw errors logged server-side only, never sent to frontend

**Pydantic Model Pattern:**
```python
class Finding(BaseModel):
    vector: str
    severity: Literal["critical", "warning", "suggestion"]
    description: str
    location: str
    evidence: str
    suggested_fix: str
```
- All models inherit `BaseModel`
- Use `Literal` for enums, not string
- Required fields only — no `Optional` unless genuinely optional
- No default values that hide missing data

### Communication Patterns

**WebSocket Event Flow:**
- Frontend connects to both `/ws/chat/{session_id}` and `/ws/status/{session_id}`
- Chat WS: bidirectional — user sends input, system sends messages/questions/checkpoints
- Status WS: server→client only — pipeline stage updates, progress, completion
- Reconnection: frontend auto-reconnects with same session_id, server replays current state

**React State (useReducer):**
```typescript
type Action =
  | { type: "CHAT_MESSAGE"; payload: ChatMessage }
  | { type: "STAGE_UPDATE"; payload: StageUpdate }
  | { type: "CHECKPOINT"; payload: CheckpointData }
  | { type: "COMPLETE"; payload: CompletionData }
  | { type: "ERROR"; payload: ErrorData }
```
- Action types: `UPPER_SNAKE_CASE`
- Payload types match WebSocket message payloads
- Reducer is pure — no side effects, no async
- WebSocket hooks dispatch actions to reducer

### Process Patterns

**Error Handling:**
- Backend: every agent function wrapped in try/except. Exceptions caught, logged with `logging.error()`, converted to user-friendly message, streamed via status WS
- Frontend: error messages rendered as system chat messages with appropriate styling. Never raw errors
- LLM failures: retried in LLM service (3x exponential backoff). If all retries fail, pipeline streams recoverable error to frontend

**Loading/Progress States:**
- Pipeline stages: `pending` → `active` → `complete` (or `error`)
- Stage descriptions always plain language: "Designing your agent architecture..." not "Running architect node"
- Progress streamed via status WS as stages transition
- Frontend sidebar reflects current stage state in real-time

### Enforcement Guidelines

**All AI Agents MUST:**
1. Follow the dependency direction: models ← services ← agents ← pipeline ← main. No reverse imports.
2. Use absolute imports: `from app.models.state import FrankensteinState`
3. Never expose raw errors to frontend — all user-facing messages must be plain language
4. Use Pydantic models for all data structures — no raw dicts crossing module boundaries
5. Use type hints on all function signatures
6. Match WebSocket message type strings exactly as defined above — frontend and backend must agree

**Anti-Patterns to Avoid:**
- Putting business logic in Pydantic models (models are data containers only)
- Agents importing from other agents (use pipeline state for data passing)
- Frontend components managing their own WebSocket connections (use the shared hook)
- Mixing Frankenstein's naming conventions with generated code conventions
- Using `print()` instead of `logging` module
- Hardcoding model names — use config for LLM model mapping

## Project Structure & Boundaries

### Complete Project Directory Structure

```
frankenstein/
├── README.md
├── .env.example                    # OpenRouter key, model mappings, iteration caps
├── .gitignore
├── docker-compose.yaml             # Post-MVP: backend + chroma + runner
│
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile                  # Post-MVP
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app, REST endpoints, WS handlers
│   │   ├── config.py               # pydantic-settings: env vars, model mapping, constants
│   │   │
│   │   ├── models/                 # Pydantic models ONLY — no business logic
│   │   │   ├── __init__.py
│   │   │   ├── state.py            # FrankensteinState (pipeline state object)
│   │   │   ├── requirements.py     # RequirementsDoc, DataSpec, ProcessStep, EdgeCase
│   │   │   ├── spec.py             # AgentSpec (the YAML schema as Pydantic)
│   │   │   ├── critique.py         # CritiqueReport, Finding
│   │   │   ├── testing.py          # TestCase, TestReport, FailureTrace
│   │   │   ├── learning.py         # BuildOutcome
│   │   │   ├── tools.py            # ToolSchema
│   │   │   └── messages.py         # WebSocket message types (chat, status, error, control)
│   │   │
│   │   ├── agents/                 # One file per pipeline agent
│   │   │   ├── __init__.py
│   │   │   ├── elicitor.py         # FR1-9: prompt analysis, gap detection, Q&A loop
│   │   │   ├── architect.py        # FR10-19: RAG query, task decomp, spec generation
│   │   │   ├── critic.py           # FR20-26: attack vectors, critique report
│   │   │   ├── builder.py          # FR31-36: code compilation, template rendering
│   │   │   ├── tester.py           # FR37-45: test gen, execution, failure tracing
│   │   │   └── learner.py          # FR46-49: outcome structuring, Chroma write-back
│   │   │
│   │   ├── pipeline/               # Graph definition + routing ONLY
│   │   │   ├── __init__.py
│   │   │   ├── graph.py            # StateGraph definition, node registration, edges
│   │   │   └── routing.py          # route_after_critique, route_after_test
│   │   │
│   │   ├── services/               # Shared stateless services
│   │   │   ├── __init__.py
│   │   │   ├── llm_service.py      # FR55-58: OpenRouter client, model routing, retry, structured output
│   │   │   ├── chroma_service.py   # FR10,47-54: collection mgmt, RAG queries, write-back
│   │   │   └── session_service.py  # Session UUID mgmt, generated agent directory mgmt
│   │   │
│   │   ├── templates/              # Code generation templates for Builder
│   │   │   ├── crewai/             # CrewAI project template files
│   │   │   │   ├── main.py.j2
│   │   │   │   ├── agents.py.j2
│   │   │   │   ├── tools.py.j2
│   │   │   │   └── orchestration.py.j2
│   │   │   └── langgraph/          # LangGraph project template files
│   │   │       ├── main.py.j2
│   │   │       ├── nodes.py.j2
│   │   │       ├── tools.py.j2
│   │   │       └── graph.py.j2
│   │   │
│   │   └── tool_library/           # Pre-seeded tool schema JSON files
│   │       ├── pdf_parser.json     # FR51
│   │       ├── financial_calculator.json
│   │       ├── rule_engine.json
│   │       ├── report_generator.json
│   │       ├── csv_parser.json     # FR52
│   │       ├── statistical_analyzer.json
│   │       ├── scoring_engine.json
│   │       ├── data_visualizer.json
│   │       ├── web_search.json     # FR53
│   │       ├── file_reader.json
│   │       ├── json_transformer.json
│   │       ├── llm_reasoner.json
│   │       └── code_executor.json
│   │
│   └── tests/
│       ├── __init__.py
│       ├── test_elicitor.py
│       ├── test_architect.py
│       ├── test_critic.py
│       ├── test_builder.py
│       ├── test_tester.py
│       ├── test_learner.py
│       ├── test_llm_service.py
│       ├── test_chroma_service.py
│       ├── test_pipeline.py        # Integration: full graph execution
│       └── test_routing.py
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── index.html
│   └── src/
│       ├── App.tsx                  # Root: layout grid (chat + sidebar)
│       ├── main.tsx                 # Entry point
│       ├── index.css                # Tailwind directives + Geist font import
│       │
│       ├── components/              # FR59-64: all UI components
│       │   ├── ChatMessage.tsx
│       │   ├── QuestionGroup.tsx
│       │   ├── RequirementsCard.tsx
│       │   ├── AgentSpecCard.tsx
│       │   ├── FlowDiagram.tsx
│       │   ├── CritiqueFinding.tsx
│       │   ├── PipelineSidebar.tsx
│       │   ├── StageIndicator.tsx
│       │   ├── ProgressTracker.tsx
│       │   ├── CompletionCard.tsx
│       │   ├── PhaseDivider.tsx
│       │   ├── TypingIndicator.tsx
│       │   └── PromptInput.tsx
│       │
│       ├── hooks/
│       │   ├── useWebSocket.ts      # WS connection mgmt for both endpoints
│       │   └── usePipelineState.ts   # Convenience hook wrapping context
│       │
│       ├── context/
│       │   ├── PipelineContext.tsx   # React context provider
│       │   └── pipelineReducer.ts   # useReducer: actions, state shape, transitions
│       │
│       ├── types/
│       │   ├── messages.ts          # WS message types (mirrors backend messages.py)
│       │   ├── pipeline.ts          # Pipeline stage, state types
│       │   └── spec.ts              # AgentSpec display types
│       │
│       └── utils/
│           └── formatters.ts        # Timestamp formatting, message formatting
│
├── runner/                          # Post-MVP
│   └── Dockerfile                   # frankenstein-runner base image
│
└── generated_agents/                # Runtime: generated agent projects stored here
    └── {session_id}/                # One directory per build session
        └── generated_agent/         # Complete agent project (zipped for download)
```

### Architectural Boundaries

**API Boundaries:**

| Endpoint | Type | Purpose | Handler Location |
|----------|------|---------|-----------------|
| `POST /sessions` | REST | Create new build session | `main.py` |
| `GET /sessions/{id}/download` | REST | Download generated agent zip | `main.py` |
| `POST /sessions/{id}/approve` | REST | Checkpoint approval | `main.py` |
| `/ws/chat/{session_id}` | WebSocket | Bidirectional: Elicitor Q&A, checkpoints, messages | `main.py` |
| `/ws/status/{session_id}` | WebSocket | Server→client: pipeline stage updates, progress | `main.py` |

**Component Boundaries:**

```
Frontend (React)          Backend (FastAPI)           Pipeline (LangGraph)
─────────────────        ──────────────────          ─────────────────────
Components ←── Context    main.py (endpoints)         graph.py (StateGraph)
    ↑                        ↓                            ↓
Hooks (WS) ←──────── WebSocket ──────────→ Pipeline ── agents/*.py
    ↑                        ↓                            ↓
Reducer  ←── Actions    session_service          services/ (llm, chroma)
```

- Frontend ONLY talks to backend via WebSocket + REST. Never directly to pipeline or services.
- Pipeline agents ONLY communicate through `FrankensteinState`. No direct agent-to-agent calls.
- Services are stateless — called by agents, never call agents.
- Models are imported everywhere but import nothing from the app.

**Data Boundaries:**

| Data Store | Owner | Readers | Write Pattern |
|-----------|-------|---------|---------------|
| `FrankensteinState` | Pipeline (LangGraph) | All agents, main.py (for WS streaming) | Agents write to state after each node execution |
| Chroma `tool_schemas` | Pre-seeded JSON files | Architect | Read-only at runtime |
| Chroma `spec_patterns` | Learner | Architect | Learner writes after each build |
| Chroma `anti_patterns` | Learner | Architect | Learner writes after failures |
| Filesystem `generated_agents/` | Builder | Tester, session_service (for zip) | Builder writes, Tester reads, session_service zips |

### Requirements to Structure Mapping

| FR Category | Backend Location | Frontend Location |
|-------------|-----------------|-------------------|
| Requirements Elicitation (FR1-9) | `agents/elicitor.py` | `QuestionGroup.tsx`, `RequirementsCard.tsx` |
| Architecture & Spec (FR10-19) | `agents/architect.py`, `services/chroma_service.py` | `AgentSpecCard.tsx`, `FlowDiagram.tsx` |
| Adversarial Review (FR20-26) | `agents/critic.py`, `pipeline/routing.py` | `CritiqueFinding.tsx` |
| Spec Review (FR27-30) | `main.py` (checkpoint handling) | `AgentSpecCard.tsx`, `FlowDiagram.tsx`, `CritiqueFinding.tsx` |
| Code Generation (FR31-36) | `agents/builder.py`, `templates/` | — |
| Testing (FR37-45) | `agents/tester.py` | `ProgressTracker.tsx` |
| Learning (FR46-49) | `agents/learner.py`, `services/chroma_service.py` | — |
| Tool Schema Library (FR50-54) | `tool_library/*.json`, `services/chroma_service.py` | — |
| LLM Service (FR55-58) | `services/llm_service.py`, `config.py` | — |
| Frontend (FR59-64) | `main.py` (WS handlers) | All components |

### Cross-Cutting Concerns Mapping

| Concern | Backend Files | Frontend Files |
|---------|--------------|----------------|
| State serialization | `models/state.py`, `models/messages.py` | `types/messages.ts`, `types/pipeline.ts` |
| LLM retry/timeout | `services/llm_service.py` | — |
| Error handling | All `agents/*.py`, `main.py` | `pipelineReducer.ts`, `ChatMessage.tsx` |
| WebSocket protocol | `main.py`, `models/messages.py` | `useWebSocket.ts`, `types/messages.ts` |
| Session management | `services/session_service.py` | `useWebSocket.ts` (session_id in URL) |

### Data Flow

```
User prompt
    → WS chat → main.py → Pipeline.invoke(state)
        → Elicitor → state.requirements
            → WS chat ← questions to user
            → WS chat → user answers
        → state.requirements_approved (checkpoint via REST)
        → Architect → state.spec
            → chroma_service.query() for RAG
        → Critic → state.critique
            → routing.py → loop or proceed
        → state.spec_approved (checkpoint via REST)
        → Builder → filesystem: generated_agents/{session_id}/
        → Tester → state.test_results
            → subprocess execution of generated code
            → routing.py → loop or proceed
        → Learner → chroma_service.write()
    → WS status ← stage updates throughout
    → REST /download ← zip file
```

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:** All technology choices (FastAPI, LangGraph, Chroma, React, Vite) work together without version conflicts. Chroma embedded runs in-process with FastAPI. LangGraph StateGraph executes in-process. No microservice overhead.

**Pattern Consistency:** Python PEP 8 (snake_case) for backend, PascalCase for React components, dot-notation WS message types — all conventions are internally consistent and match framework expectations. Pydantic models as the universal data layer prevent format mismatches between agents, pipeline, and API.

**Structure Alignment:** Project structure directly supports all architectural decisions. Separate WS endpoints map to separate handler functions in `main.py`. Named session directories enable the REST download endpoint. Template directories support the two-compiler Builder pattern.

### Requirements Coverage Validation ✅

**Functional Requirements Coverage:** All 64 FRs mapped to specific backend files and frontend components. No orphan requirements — every FR has an implementation home in the project structure.

**Non-Functional Requirements Coverage:**
- Performance: In-process architecture (no network hops between pipeline stages), centralized LLM retry, performance budget defined per stage
- Security: API keys in `.env` loaded by pydantic-settings, never transmitted via WS, generated agent keys injected via config.yaml
- Integration: OpenRouter as sole LLM gateway, Chroma embedded, pip-only generated code

### Implementation Readiness Validation ✅

**Decision Completeness:** All critical and important decisions documented with rationale. Technology versions identified. Deferred decisions (auth, Docker, cloud deploy) explicitly listed with upgrade paths.

**Structure Completeness:** Complete file tree with every directory and file named. FR-to-file mapping table provides direct lookup for implementors.

**Pattern Completeness:** Naming conventions cover Python, TypeScript, WS messages, and pipeline state. Dependency direction rule prevents circular imports. Anti-patterns listed.

### Gap Analysis Results

**Critical Gaps:** None

**Minor Gaps:**
1. **Jinja2 dependency** — `templates/*.j2` files require `jinja2` package. Must be added to `backend/requirements.txt`.
2. **Session cleanup** — `generated_agents/` directory cleanup strategy not specified. Recommend: clean on server startup + optional TTL-based cleanup.
3. **CORS configuration** — Frontend (Vite dev on port 5173) → Backend (uvicorn on port 8000) requires CORS middleware in FastAPI or Vite proxy config.

### Validation Issues Addressed

All three minor gaps documented above. None block implementation — they are configuration items to include during project initialization.

### Architecture Completeness Checklist

**Requirements Analysis**

- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**

- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**Implementation Patterns**

- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**Project Structure**

- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High — all 16 checklist items checked, no critical gaps, all 64 FRs mapped to implementation locations.

**Key Strengths:**
- Pre-decided stack eliminates analysis paralysis — architecture doc codifies existing decisions into enforceable rules
- Single-process architecture keeps hackathon complexity low while allowing future decomposition
- Pipeline state as single source of truth prevents agent-to-agent coupling
- Two-layer separation (Frankenstein code vs generated code) with distinct naming conventions prevents confusion
- Complete FR-to-file mapping gives implementors zero ambiguity about where code goes

**Areas for Future Enhancement:**
- Pipeline state persistence (SQLite checkpoint) for production reliability
- Docker execution sandbox for generated agents
- Authentication and multi-tenancy
- CI/CD pipeline and deployment automation
- Comprehensive integration test suite beyond unit tests

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and boundaries — dependency direction is models ← services ← agents ← pipeline ← main
- Refer to this document for all architectural questions
- Use absolute imports throughout backend
- Match WebSocket message type strings exactly between backend and frontend

**First Implementation Priority:**
1. Project scaffold (directories + config files)
2. Pydantic models in `models/` (data foundation)
3. `config.py` with pydantic-settings
4. `llm_service.py` (all agents depend on this)
5. `chroma_service.py` + tool library seeding
