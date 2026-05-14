---
stepsCompleted: ['step-01-requirements-extracted', 'step-02-epics-designed', 'step-03-stories-complete', 'step-04-validated']
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
---

# Frankenstein - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Frankenstein, decomposing the requirements from the PRD, UX Design, and Architecture into implementable stories.

## Scope Decisions

Resolved contradictions between PRD FRs and PRD Scope section:

| Decision | Resolution |
|----------|-----------|
| Spec-level failure routing (FR42/43 vs Nice-to-Have) | FailureTrace classifies both levels. MVP routing: code-level → Builder only. Spec-level failures → Learner with partial_success flag. |
| Anti-pattern memory (FR48-49 vs Nice-to-Have) | Keep FRs. Learner writes anti-patterns. Architect queries gracefully handle empty results (cold start). |
| Spec pattern RAG (FR10 vs Growth Feature) | Keep FR. Architect queries spec_patterns. Empty results on first build = works from first principles. |
| Critic vectors (6 in Solution Approach vs 3 must-have) | 3 must-have: Format Compatibility (FR20), Tool Validation (FR21), Dependency Completeness (FR22). Other 3 (dead-end, resource conflicts, circular deps) are post-MVP. |
| Execution isolation (Docker vs subprocess) | Local subprocess with timeout for MVP (per Architecture doc). Docker post-MVP. |

## Requirements Inventory

### Functional Requirements

**Requirements Elicitation (FR1-9)**

FR1: User can submit a natural language prompt describing the agent they want built
FR2: System can analyze the prompt against a 5-category completeness checklist (Input/Output, Process, Data, Edge Cases, Quality Bar) and assign confidence scores (0-1) per field
FR3: System can generate targeted questions only for fields scoring below 0.7 confidence
FR4: User can answer Elicitor questions through a real-time chat interface
FR5: System can loop up to 3 question rounds; after 3 rounds, remaining gaps are flagged as assumptions in the requirements doc
FR6: System can compile answers into a structured RequirementsDoc (domain, inputs, outputs, process steps, edge cases, quality criteria, constraints)
FR7: User can review the generated requirements document in a readable rendered format at human checkpoint 1
FR8: User can approve the requirements, or provide free-text corrections that the Elicitor incorporates before re-presenting
FR9: System can handle low-quality or empty prompts by generating at least 2 clarifying questions per identified gap to guide the user toward sufficient input

**Architecture & Specification (FR10-19)**

FR10: System can query Chroma spec_patterns collection for similar past specs via RAG (graceful on empty — works from first principles when no past specs exist)
FR11: System can decompose requirements process_steps into discrete computational tasks, each tagged with required capability (text extraction, calculation, reasoning, generation, API call)
FR12: System can query the Tool Schema Library for each task's capability and receive ranked tool matches with format compatibility info
FR13: System can select tools based on format chain compatibility (upstream output format matches downstream input format)
FR14: System can group tasks into agents based on cohesion (related tasks) and coupling (data dependencies)
FR15: System can design memory strategy (short-term, long-term, shared, none) based on inter-agent data sharing needs
FR16: System can analyze the dependency graph to determine execution flow pattern (sequential, parallel, hierarchical, graph)
FR17: System can select target framework — CrewAI for role-based crews, LangGraph for state-dependent flows — based on flow pattern analysis
FR18: System can generate a complete AgentSpec (agents, tools, memory, execution flow, error handling, I/O contracts) as structured output conforming to the defined spec schema
FR19: System can expose decision rationale for framework selection, tool choices, and agent grouping in the spec output

**Adversarial Review (FR20-26)**

FR20: Critic can run format compatibility checks — verify every agent's output format matches the next agent's input format across all edges
FR21: Critic can run tool validation — verify each tool's accepts field matches the data format it will actually receive
FR22: Critic can run dependency completeness checks — verify every agent's required input fields are provided by upstream agents
FR23: Critic can generate a CritiqueReport with findings scored as critical, warning, or suggestion, including evidence and suggested fixes
FR24: System can route specs with critical findings back to Architect for revision, attaching critique findings to state
FR25: System can loop Architect-Critic review until no critical findings remain, up to a configurable max iteration cap
FR26: Architect and Critic must use different LLM model families to ensure cross-model adversarial coverage

**Spec Review & Approval (FR27-30)**

FR27: User can view the architectural spec rendered with agent roles, assigned tools, and a visual flow diagram (graph visualization of agent connections and data flow)
FR28: User can view the Critic's findings with severity color coding (critical/warning/suggestion)
FR29: User can view the Architect's decision rationale (why this framework, why these tools, why this grouping)
FR30: User can approve the spec, or provide free-text feedback that triggers Architect revision before re-presenting

**Code Generation (FR31-36)**

FR31: Builder can compile a validated AgentSpec into CrewAI code that follows the framework's documented patterns (Agent, Tool, Crew definitions)
FR32: Builder can compile a validated AgentSpec into LangGraph code that follows the framework's documented patterns (StateGraph, node functions, conditional edges)
FR33: Builder can generate a complete project directory: main.py, agents.py, tools.py, orchestration.py, config.yaml, requirements.txt, tests/
FR34: Builder can use pre-validated code templates from the Tool Schema Library for tool implementations
FR35: Builder can validate generated code — syntax check (py_compile), import resolution against requirements.txt, function signature match against spec I/O contracts
FR36: Builder can generate a README.md in the output with usage instructions, config.yaml field descriptions, and run command

**Testing & Validation (FR37-45)**

FR37: Tester can generate test cases from spec I/O contracts, including expected output schemas and quality checks
FR38: Tester can generate synthetic test input data based on domain knowledge from the requirements doc
FR39: Tester can execute generated agent code in a local subprocess with a configurable timeout (default 60s)
FR40: Tester can capture stdout, stderr, and exit code from execution
FR41: Tester can validate execution output against expected output schemas and quality checks
FR42: Tester can generate FailureTraces mapping errors to the failing agent, root cause classification (code-level vs spec-level), and suggested fix
FR43: Tester can route code-level failures back to Builder for code fixes (spec-level failures route to Learner with partial_success flag for MVP)
FR44: System can loop Builder-Tester until tests pass, up to a configurable max iteration cap
FR45: System can deliver a partially successful build when max iterations are reached, with clear warnings about what failed and why

**Learning & Memory (FR46-49)**

FR46: Learner can structure build outcomes: requirements summary, final spec, framework used, tools used, iterations needed, failure patterns, anti-patterns, success patterns
FR47: Learner can write build outcomes to Chroma spec_patterns collection for future RAG retrieval
FR48: Learner can write failure patterns to Chroma anti_patterns collection (graceful — writes when patterns exist, no-op when none)
FR49: Architect can query anti_patterns collection to check if a proposed pattern has failed before (graceful on empty)

**Tool Schema Library (FR50-54)**

FR50: System can store validated tool definitions with id, name, description, category, accepts, outputs, output_format, limitations, dependencies, code_template, compatible_with, incompatible_with
FR51: System ships pre-seeded with tools for PS-08 (PDF parser, OCR, financial calculator, rule engine, report generator)
FR52: System ships pre-seeded with tools for PS-06 (csv_parser, statistical_analyzer, scoring_engine, data_visualizer, report_generator)
FR53: System ships pre-seeded with general-purpose tools (web_search, file_reader, json_transformer, llm_reasoner, code_executor)
FR54: Architect can query tool library by capability requirement and receive ranked matches with format compatibility info

**LLM Service (FR55-58)**

FR55: System can route LLM calls through OpenRouter with model-per-agent configuration
FR56: System can retry failed LLM calls with exponential backoff (3 retries)
FR57: System can parse LLM responses into structured Pydantic models via JSON mode
FR58: Generated agents that require LLM access receive the API key injected via config.yaml at build time

**Frontend Experience (FR59-64)**

FR59: User can interact with the Elicitor via real-time WebSocket chat
FR60: User can see which pipeline stage is currently executing, with visual progress indication
FR61: User can see test results after the Tester completes (pass/fail per test, generated agent output)
FR62: User can download the generated agent project as a zip file
FR63: User can start a new build session
FR64: User can see error states when pipeline stages fail (LLM errors, build failures) with clear messaging

**Added Requirements (from Architecture + Solution Approach, not in original PRD)**

FR65: Elicitor queries Chroma domain_insights collection for domain-specific context before prompt analysis (graceful on empty — skips when no insights exist)
FR66: System provides session management service for UUID generation, generated agent directory lifecycle, and zip packaging
FR67: Backend defines typed WebSocket message Pydantic models for all message types: chat (message, question_group, checkpoint), status (stage_update, progress, complete), error (llm_failure, pipeline_failure), control (approve, reject, user_input)

### NonFunctional Requirements

NFR1: End-to-end prompt-to-working-agent completes in under 10 minutes on a standard dev machine (8GB RAM, 4-core CPU), including human interaction time
NFR2: Performance budget by stage: Elicitor Q&A ~2-3 min (human-bound), Architect+Critic ~2-3 min, Builder ~1 min, Tester ~1-2 min, Learner <30s
NFR3: WebSocket chat messages deliver to frontend within 500ms of generation
NFR4: Pipeline stage transitions reflect in the UI within 1 second
NFR5: Spec rendering (agents, tools, flow diagram) loads within 2 seconds of generation
NFR6: Zip file generation and download initiates within 3 seconds of build completion
NFR7: LLM calls that exceed 60 seconds per individual call timeout and retry
NFR8: OpenRouter API key stored server-side, never exposed to frontend
NFR9: API key for generated agents injected via config.yaml, not hardcoded in generated source code
NFR10: Generated code execution has a configurable timeout (default 60s) to prevent runaway processes
NFR11: No user authentication required for hackathon demo
NFR12: All LLM calls route through OpenRouter API with model-per-agent routing
NFR13: Chroma runs as an embedded instance (no separate server)
NFR14: Frontend-backend communication via WebSocket for chat and pipeline streaming, REST for file download and checkpoint approvals
NFR15: Generated agent code depends only on packages available via pip (no private registries)
NFR16: Session state is in-memory only — does not survive server restart (hackathon scope)
NFR17: Single concurrent session supported (hackathon scope — no multi-tenancy)

### Additional Requirements

- WebSocket protocol: separate endpoints `/ws/chat/{session_id}` for conversation, `/ws/status/{session_id}` for pipeline events
- WebSocket message format: type-tagged JSON `{type: string, payload: object, timestamp: string, session_id: string}`
- WebSocket message type strings use dot notation: `chat.message`, `chat.question_group`, `chat.checkpoint`, `status.stage_update`, `status.progress`, `status.complete`, `error.llm_failure`, `error.pipeline_failure`, `control.approve`, `control.reject`, `control.user_input`
- REST endpoints: POST `/sessions` (create), GET `/sessions/{id}/download` (zip), POST `/sessions/{id}/approve` (checkpoint)
- Session management: UUID per session, passed as path param on WS connect
- Generated agent storage: named directory per session `generated_agents/{session_id}/`
- Error responses: structured `{type: "error", payload: {stage, message, recoverable}}`
- User-facing error messages must be plain language, never raw errors or stack traces
- Dependency direction: models <- services <- agents <- pipeline <- main (no reverse imports)
- Absolute imports throughout backend: `from app.models.state import FrankensteinState`
- Pydantic models for all data structures — no raw dicts crossing module boundaries
- Jinja2 templates for Builder code generation (`templates/crewai/*.j2`, `templates/langgraph/*.j2`)
- CORS configuration: frontend (Vite port 5173) to backend (uvicorn port 8000)
- Session cleanup: clean generated_agents/ on server startup
- Execution isolation: local subprocess with timeout (MVP), Docker post-MVP
- Logging: Python `logging` to stdout, never `print()`
- Environment config: `.env` file, pydantic-settings for typed config loading
- Generated code follows target framework conventions (CrewAI/LangGraph naming), NOT Frankenstein conventions
- Builder templates enforce framework-idiomatic output — not left to LLM discretion

### UX Design Requirements

**Design System (UX-DR1-4)**

UX-DR1: Dark-mode-first design system using Tailwind CSS + shadcn/ui, with warm near-black background (#0a0a0a), surface (#171717), surface-elevated (#262626), border (#2e2e2e)
UX-DR2: Typography system using Geist Sans (primary) and Geist Mono (code), with defined type scale from 11px caption to 24px page title
UX-DR3: Warm amber accent color (#f59e0b) used only on interactive elements and completion moments — never decorative
UX-DR4: Semantic colors: critical (red #ef4444 80%), warning (amber 80%), success (green #22c55e 80%), info (blue #3b82f6 60%) — used contextually only

**Layout & Entry (UX-DR5-6)**

UX-DR5: Clean-slate entry screen — single prompt input, dark background, logo "Frankenstein" (28px, weight 700), tagline "Describe your workflow. Get working AI agents." (14px, tertiary), no other elements
UX-DR6: Two-panel layout after first prompt: main chat thread (left, ~75%, max-width 720px) + persistent pipeline sidebar (right, 240px fixed). CSS Grid: `grid-template-columns: 1fr 240px`

**Components (UX-DR7-19)**

UX-DR7: ChatMessage component — system variant (surface-elevated, full-width) and user variant (transparent, 48px left indent), with fade-up 12px entry animation (250ms ease-out)
UX-DR8: QuestionGroup component — categorized Elicitor questions with amber category labels (11px uppercase), left-bordered questions (2px), surface-elevated container (12px border-radius, 20px padding)
UX-DR9: RequirementsCard component — checkpoint 1 approval card with key-value requirement rows, Approve (amber primary) + Edit (outline secondary) buttons
UX-DR10: AgentSpecCard component — displays one agent from spec blueprint with role name (14px, weight 600), description (13px, secondary), tool tags in monospace badges. Grid: `repeat(auto-fit, minmax(240px, 1fr))`
UX-DR11: FlowDiagram component — horizontal directed graph of agent execution flow with rounded-rectangle nodes (surface-elevated, 8px border-radius), arrow connectors, condition labels (11px)
UX-DR12: CritiqueFinding component — severity-badged findings (10px uppercase badge: critical red, warning amber, suggestion green) with expandable evidence + suggested fix via Accordion
UX-DR13: PipelineSidebar component — persistent right sidebar with "Pipeline" title (11px uppercase), stage list with connecting lines, hidden pre-first-prompt, fade-in from right (300ms)
UX-DR14: StageIndicator component — 20px status dot (pending: gray, active: amber pulse, done: green checkmark), stage name (13px, weight 500), description (11px), connecting line (1px)
UX-DR15: ProgressTracker component — inline build progress with header (18px), progress bar (4px height, amber fill, smooth 400ms transition), stage rows with icons (32px) and timing
UX-DR16: CompletionCard component — 64px green checkmark circle, "Your agents are ready." (22px, weight 600), summary table (agents, framework, tests, build time, files), amber "Download Agent Project" button, staggered fade-up entry
UX-DR17: PhaseDivider component — horizontal line (1px, border color) with centered uppercase label (11px, tertiary, 0.05em spacing), opacity fade-in 400ms, 32px vertical margin
UX-DR18: TypingIndicator component — opacity pulse (0.4 to 1 to 0.4, 1.5s cycle), not bouncing dots
UX-DR19: PromptInput component — fixed position bottom of viewport, surface-elevated, disabled during autonomous phases with "Frankenstein is working..." placeholder, Send on Enter, Shift+Enter for newline

**Interaction Patterns (UX-DR20-30)**

UX-DR20: Button hierarchy: primary (amber bg, dark text, weight 600), secondary (transparent, border, weight 500), ghost (no bg/border) — max one primary visible at a time. Press: scale 0.97 (100ms)
UX-DR21: Micro-animation system: fade-up entry (250ms), approve press scale (0.97, 100ms), progress bar fill (400ms ease-in-out), stage completion checkmark (50ms scale 0.8→1), spec cards staggered fade-up (250ms each, 50ms stagger), sidebar fade-in from right (300ms), critique badge slide-in (4px, 200ms). No bounce easing ever. Respect prefers-reduced-motion
UX-DR22: Chat message spacing: 8px gap between consecutive same-type, 16px between type switches, 32px + PhaseDivider between phases
UX-DR23: Auto-scroll to newest message, but stop if user scrolled up — show "New messages ↓" indicator. Smooth scroll 300ms
UX-DR24: Frontend state management: React context + useReducer, no external state library
UX-DR25: Single useWebSocket hook managing both WS connections, dispatching actions to reducer
UX-DR26: Frontend types mirror backend message types (messages.ts mirrors messages.py)
UX-DR27: Desktop-only, minimum 1024px width, sidebar collapses below 1024px
UX-DR28: Accessibility: WCAG AA contrast, 44px min touch targets, prefers-reduced-motion respected, semantic HTML, focus indicators (2px amber outline)
UX-DR29: Partial success variant: amber checkmark instead of green, subtitle "mostly ready", amber test count, download still available
UX-DR30: Phase transition labels: "Understanding your needs", "Requirements Summary", "Your Blueprint", "Building", "Delivery"
UX-DR31: Toast notifications for stage completion (auto-dismiss 3s) and download ready
UX-DR32: Tooltip on tool names in spec review showing tool description
UX-DR33: Progress messaging uses plain language: "Designing your agent architecture..." not "Running architect node". Iteration framed as "refining/improving", never "error/retry"

### FR Coverage Map

| FR | Epic | Description |
|---|---|---|
| FR1-9 | Epic 1 | Requirements elicitation (Elicitor agent, Q&A loop, checkpoint 1) |
| FR10-19 | Epic 2 | Architecture & specification (Architect agent, RAG, spec generation) |
| FR20-26 | Epic 2 | Adversarial review (Critic agent, 3 attack vectors, feedback loop) |
| FR27-30 | Epic 2 | Spec review & approval (visual rendering, checkpoint 2) |
| FR31-36 | Epic 3 | Code generation (Builder, CrewAI + LangGraph compilers, templates) |
| FR37-45 | Epic 3 | Testing & validation (Tester, subprocess execution, failure tracing) |
| FR46-48 | Epic 3 | Learning & memory (Learner, Chroma write-back) |
| FR49 | Epic 2 | Anti-pattern query (Architect queries before designing) |
| FR50-54 | Epic 2 | Tool schema library (already built — Architect needs for RAG) |
| FR55-57 | Epic 1 | LLM service (already built — model routing, retry, JSON mode) |
| FR58 | Epic 3 | API key injection in generated agent config.yaml |
| FR59 | Epic 1 | WebSocket chat for Elicitor interaction |
| FR60 | Epic 3 | Pipeline stage progress indicator |
| FR61 | Epic 3 | Test results display |
| FR62 | Epic 3 | Zip download of generated agent |
| FR63 | Epic 1 | Start new build session |
| FR64 | Epic 3 | Error state display |
| FR65 | Epic 1 | Domain insights RAG query (Elicitor pre-analysis) |
| FR66 | Epic 1 | Session management service |
| FR67 | Epic 1 | WebSocket message type models |

**All 67 FRs covered. Zero orphans.**

## Epic List

### Epic 1: Conversational Requirements Discovery

A user can describe a workflow in natural language, answer intelligent follow-up questions, and approve a structured requirements document — all through a real-time chat interface.

**User outcome:** User types a fuzzy prompt, receives smart domain-aware questions, responds conversationally, and approves a structured requirements document. The Elicitor understands their domain and asks what matters.

**FRs covered:** FR1-9, FR55-57, FR59, FR63, FR65-67
**NFRs addressed:** NFR3, NFR7-8, NFR11-14, NFR16-17
**UX-DRs:** UX-DR1-9, UX-DR17-25, UX-DR27-28, UX-DR30-31

**What ships:**
- FastAPI server with WebSocket endpoints (chat + status)
- Session management service (UUID, directory lifecycle)
- WebSocket message type models (backend + frontend types)
- LangGraph pipeline graph (initial: elicitor + checkpoint nodes)
- Elicitor agent (5-category gap analysis, Q&A loop, domain insights RAG)
- Human checkpoint 1 (requirements approval)
- Frontend: entry screen, chat thread, question groups, requirements card, prompt input, pipeline sidebar (initial)
- LLM service (already built), Chroma service (already built), Pydantic models (already built), Tool library (already built)

**Pre-completed:** Data models, LLM service, Chroma service, tool library seeding (from Layer 1 build)

---

### Epic 2: Architecture Generation & Adversarial Review

A user can see a thoughtfully designed, adversarially-reviewed agent architecture blueprint with visual spec cards, flow diagram, and critique findings, then approve or request changes.

**User outcome:** After requirements approval, the system designs an agent architecture informed by past patterns and the tool library, then a different AI model attacks the design for flaws. User sees the blueprint in plain language — agent roles, tools, flow diagram, critique findings with severity — and approves or requests changes.

**FRs covered:** FR10-30, FR49-54
**UX-DRs:** UX-DR10-14, UX-DR32-33

**What ships:**
- Architect agent (RAG queries: spec patterns, tool library, anti-patterns → task decomposition → tool matching → agent grouping → flow design → memory design → compile spec)
- Critic agent (3 attack vectors: format compatibility, tool validation, dependency completeness)
- Architect-Critic feedback loop (route_after_critique, MAX_SPEC_ITERATIONS cap)
- Human checkpoint 2 (spec approval with free-text feedback)
- Pipeline graph extensions (architect, critic, routing, checkpoint 2 nodes)
- Frontend: agent spec cards, flow diagram, critique findings with severity badges, spec approval UI
- Tool library RAG integration (already built — queries used by Architect)

**Depends on:** Epic 1 (pipeline graph, session, WebSocket, chat UI)

## Epic 1: Conversational Requirements Discovery

A user can describe a workflow in natural language, answer intelligent follow-up questions, and approve a structured requirements document — all through a real-time chat interface.

### Story 1.1: Project Bootstrap & Server Infrastructure

As a **developer**,
I want a running FastAPI server with WebSocket endpoints, session management, and typed message models,
So that the backend is ready to support the pipeline and frontend communication.

**Acceptance Criteria:**

**Given** the backend server is started with `uvicorn app.main:app`
**When** a client sends GET to `/health`
**Then** the server responds with 200 and `{"status": "ok"}`

**Given** CORS is configured
**When** the frontend at localhost:5173 makes a request
**Then** the request is allowed (Access-Control-Allow-Origin)

**Given** a client sends POST to `/sessions`
**When** the request is processed
**Then** a new session UUID is returned as `{"session_id": "uuid"}`
**And** a directory `generated_agents/{session_id}/` is created

**Given** a valid session_id
**When** a client connects to `/ws/chat/{session_id}`
**Then** the WebSocket connection is established and a `chat.message` welcome is sent

**Given** a valid session_id
**When** a client connects to `/ws/status/{session_id}`
**Then** the WebSocket connection is established and the current pipeline state is sent

**Given** `messages.py` is defined
**When** imported
**Then** all message types are available: `ChatMessage`, `QuestionGroupMessage`, `CheckpointMessage`, `StageUpdateMessage`, `ProgressMessage`, `CompleteMessage`, `ErrorMessage`, `ControlMessage`
**And** each has `type` (dot-notation string), `payload`, `timestamp`, `session_id` fields

**Given** `session_service.py` is defined
**When** `create_session()` is called
**Then** a UUID is generated and the session directory is created
**When** `cleanup_sessions()` is called on server startup
**Then** old `generated_agents/` directories are removed

**Covers:** FR55-57 (pre-built), FR63, FR66, FR67, NFR3, NFR8, NFR11-14, NFR16-17

---

### Story 1.2: Frontend Foundation & Chat UI

As a **user**,
I want a clean, dark chat interface where I can type my workflow description,
So that I can start building agents without friction.

**Acceptance Criteria:**

**Given** the user opens the app
**When** the page loads
**Then** they see a clean-slate entry screen: dark background (#0a0a0a), "Frankenstein" logo (28px, weight 700), tagline "Describe your workflow. Get working AI agents." (14px, tertiary), and a single prompt input with "Describe the workflow you want to automate..." placeholder
**And** no sidebar is visible

**Given** the user types a prompt and hits Enter
**When** the message is submitted
**Then** the chat message appears as a user variant (transparent bg, 48px left indent)
**And** a system TypingIndicator appears (opacity pulse 0.4→1→0.4, 1.5s)
**And** the PipelineSidebar fades in from right (300ms) showing pipeline stages

**Given** the system sends a response
**When** the message arrives via WebSocket
**Then** a system ChatMessage appears (surface-elevated bg, full-width) with fade-up animation (12px, 250ms)

**Given** consecutive messages of the same type
**When** rendered
**Then** they have 8px gap between them
**And** 16px gap between different types
**And** 32px + PhaseDivider between phases

**Given** the PipelineSidebar is visible
**When** a stage is pending
**Then** it shows a gray dot with stage name
**When** a stage is active
**Then** it shows an amber pulsing dot with description
**When** a stage completes
**Then** it shows a green checkmark

**Given** the user scrolls up in chat history
**When** new messages arrive
**Then** a "New messages ↓" indicator appears instead of auto-scrolling

**Given** the pipeline is in an autonomous phase
**When** the input is rendered
**Then** it shows disabled state with "Frankenstein is working..." placeholder

**Given** the viewport width is below 1024px
**When** rendered
**Then** the sidebar collapses and chat goes full-width

**Covers:** FR59, UX-DR1-7, UX-DR13-14, UX-DR17-25, UX-DR27-28, UX-DR30-31

---

### Story 1.3: Elicitor Agent — Requirements Extraction

As a **user**,
I want the system to ask me smart, targeted questions about my workflow so it understands what I need,
So that the generated agents are built on solid, complete requirements — not guesswork.

**Acceptance Criteria:**

**Given** a user submits a natural language prompt via WebSocket
**When** the Elicitor processes it
**Then** it queries Chroma `domain_insights` for relevant domain context (graceful on empty)
**And** analyzes the prompt against 5 categories (Input/Output, Process, Data, Edge Cases, Quality Bar)
**And** assigns confidence scores (0.0-1.0) per category

**Given** categories score below 0.7
**When** questions are generated
**Then** targeted questions are created only for gap categories
**And** at least 2 questions per gap for low-quality/empty prompts
**And** questions are prioritized: Input/Output > Process > Data > Edge Cases > Quality Bar

**Given** questions are ready
**When** sent to frontend
**Then** they arrive as a `chat.question_group` message with category labels
**And** the QuestionGroup component renders with amber category labels (11px uppercase), left-bordered questions (2px), surface-elevated container

**Given** the user responds with answers
**When** the Elicitor processes answers
**Then** it updates the RequirementsDoc with extracted information
**And** re-scores all categories

**Given** categories still have gaps below 0.7
**When** the round count is below MAX_ELICITOR_ROUNDS (3)
**Then** the Elicitor generates follow-up questions for remaining gaps

**Given** 3 rounds are reached
**When** gaps still remain
**Then** remaining gaps are flagged as `assumptions` in the RequirementsDoc
**And** the Elicitor proceeds to compilation

**Given** all categories score >= 0.7 or max rounds reached
**When** the Elicitor compiles
**Then** a complete RequirementsDoc is produced with: domain, inputs, outputs, process_steps, edge_cases, quality_criteria, constraints, assumptions
**And** the pipeline state is updated with `requirements` and `elicitor_questions`

**Given** the LLM service is called
**When** the call is for the Elicitor
**Then** it routes to `openai/gpt-4o-mini` via OpenRouter
**And** responses are parsed as JSON (json_mode=True)

**Covers:** FR1-6, FR9, FR65, UX-DR8

---

### Story 1.4: Requirements Review & Approval Checkpoint

As a **user**,
I want to review the structured requirements document and approve or correct it,
So that I'm confident the system understood my needs before it starts designing.

**Acceptance Criteria:**

**Given** the Elicitor produces a RequirementsDoc
**When** the pipeline reaches human_checkpoint_1
**Then** the pipeline pauses execution
**And** a `chat.checkpoint` message is sent with the RequirementsDoc payload
**And** the status WS sends a `status.stage_update` with checkpoint indicator

**Given** the checkpoint message arrives at the frontend
**When** the RequirementsCard renders
**Then** it shows title "Here's what I understood — does this look right?"
**And** displays requirement items as key-value rows (bold label + description)
**And** shows Approve button (amber primary, left) + Edit button (outline secondary, right)
**And** max one primary button is visible

**Given** the user clicks Approve
**When** the approval is processed
**Then** a POST is sent to `/sessions/{id}/approve` with `{"checkpoint": "requirements", "approved": true}`
**And** the pipeline state updates `requirements_approved = true`
**And** the RequirementsCard collapses with green border flash (300ms)
**And** a chat message confirms: "Requirements approved — designing your agent architecture..."
**And** the pipeline resumes to the next node
**And** a toast notification appears "Requirements approved" (auto-dismiss 3s)

**Given** the user clicks Edit and provides free-text corrections
**When** the corrections are submitted
**Then** a `control.user_input` message is sent with the corrections
**And** the Elicitor incorporates corrections into the RequirementsDoc
**And** the updated RequirementsCard is re-presented for review
**And** `requirements_approved` remains false

**Given** the PhaseDivider
**When** transitioning from elicitation to requirements review
**Then** a divider appears with label "Requirements Summary" (11px uppercase, fade-in 400ms)

**Covers:** FR7-8, UX-DR9, UX-DR20, UX-DR30

---

## Epic 2: Architecture Generation & Adversarial Review

A user can see a thoughtfully designed, adversarially-reviewed agent architecture blueprint with visual spec cards, flow diagram, and critique findings, then approve or request changes.

### Story 2.1: Architect Agent — RAG Queries & Task Decomposition

As a **system**,
I want the Architect to query past patterns, decompose requirements into tasks, and match tools from the library,
So that spec generation is informed by real tool capabilities and past learnings.

**Acceptance Criteria:**

**Given** requirements are approved and pipeline transitions to the Architect node
**When** the Architect agent starts
**Then** it performs 3 parallel RAG queries: `find_similar_specs(requirements_summary)`, `check_anti_patterns(domain + process description)`, `find_tools_for_capability(per task)`
**And** empty results from any query are handled gracefully (first build = no prior data)

**Given** a RequirementsDoc with process_steps
**When** the Architect decomposes tasks
**Then** each process_step is mapped to one or more discrete computational tasks
**And** each task is tagged with a capability type: text_extraction, calculation, reasoning, generation, api_call

**Given** tasks with capability tags
**When** the Architect queries the Tool Schema Library
**Then** each task gets ranked tool matches via `find_tools_for_capability(capability_description)`
**And** tool selection considers format chain compatibility: upstream tool's `output_format` matches downstream tool's `accepts`

**Given** tasks with matched tools
**When** the Architect groups tasks into agents
**Then** grouping is based on cohesion (related tasks) and coupling (data dependencies)
**And** each agent gets a role name, goal description, and assigned tool references

**Given** the LLM service is called
**When** the call is for the Architect
**Then** it routes to `anthropic/claude-sonnet-4-6` via OpenRouter

**Covers:** FR10-14, FR49, FR54

---

### Story 2.2: Architect Agent — Spec Compilation

As a **system**,
I want the Architect to compile task decomposition, tool matches, and agent groupings into a complete AgentSpec,
So that the Critic has a structured, reviewable spec to attack.

**Acceptance Criteria:**

**Given** agents are grouped with tools assigned
**When** the Architect designs execution flow
**Then** it analyzes the dependency graph to determine flow pattern (sequential, parallel, hierarchical, graph)
**And** selects target framework: CrewAI for role-based crews, LangGraph for state-dependent flows

**Given** inter-agent data sharing needs
**When** the Architect designs memory strategy
**Then** each agent gets a memory config: short_term, long_term, shared, or none
**And** agents sharing data get shared memory; isolated agents get none

**Given** all design decisions are made
**When** the Architect compiles the AgentSpec
**Then** the output conforms to the AgentSpec Pydantic model: metadata, agents, tools, memory, execution_flow, error_handling, io_contracts
**And** decision_rationale is populated in metadata explaining framework selection, tool choices, and agent grouping

**Given** the compiled spec
**When** written to pipeline state
**Then** `state["spec"]` contains the complete AgentSpec
**And** `state["architect_reasoning"]` contains the decision rationale string

**Covers:** FR15-19

---

### Story 2.3: Critic Agent & Architect-Critic Feedback Loop

As a **system**,
I want a different LLM model to adversarially review the spec for format mismatches, tool errors, and missing dependencies,
So that architectural flaws are caught before code generation.

**Acceptance Criteria:**

**Given** a compiled AgentSpec in pipeline state
**When** the Critic agent runs
**Then** it executes 3 attack vectors:
1. **Format Compatibility** (FR20): verify every agent's output format matches the next agent's input format across all edges in execution_flow
2. **Tool Validation** (FR21): verify each tool's `accepts` field matches the data format it will actually receive from its agent
3. **Dependency Completeness** (FR22): verify every agent's required input fields are provided by upstream agents or initial state

**Given** the Critic finds issues
**When** generating the CritiqueReport
**Then** each finding has: vector, severity (critical/warning/suggestion), description, location, evidence, suggested_fix
**And** the report includes a summary string and iteration count

**Given** the CritiqueReport is generated
**When** `route_after_critique` evaluates it
**Then** if any finding has severity == "critical": route back to Architect with critique attached to state
**Then** if no critical findings: route to human_checkpoint_2

**Given** the spec is routed back to Architect
**When** the Architect revises
**Then** it reads `state["critique"]` findings and addresses each critical issue
**And** produces a revised AgentSpec

**Given** the Architect-Critic loop
**When** iteration count reaches MAX_SPEC_ITERATIONS (3)
**Then** the loop exits regardless of remaining criticals
**And** the spec proceeds to checkpoint 2 with unresolved findings visible

**Given** the Critic LLM call
**When** routed
**Then** it uses `openai/gpt-4o` — a different model family than the Architect (claude-sonnet-4-6) for cross-model adversarial coverage

**Covers:** FR20-26

---

### Story 2.4: Spec Review & Approval Checkpoint

As a **user**,
I want to see the agent architecture blueprint with agent cards, flow diagram, and critique findings, then approve or request changes,
So that I understand and control what gets built.

**Acceptance Criteria:**

**Given** the spec passes the Critic (or hits max iterations)
**When** the pipeline reaches human_checkpoint_2
**Then** a `chat.checkpoint` message is sent with the AgentSpec and CritiqueReport payload
**And** the status WS sends `status.stage_update` with checkpoint indicator

**Given** the checkpoint message arrives at frontend
**When** AgentSpecCards render
**Then** each agent displays: role name (14px, weight 600), description (13px, secondary), tool tags as monospace badges
**And** cards use grid layout: `repeat(auto-fit, minmax(240px, 1fr))`
**And** cards fade up with 250ms stagger (50ms between cards)

**Given** the spec includes execution_flow
**When** the FlowDiagram renders
**Then** it shows a horizontal directed graph with rounded-rectangle nodes (surface-elevated, 8px border-radius)
**And** arrow connectors between nodes with condition labels (11px)

**Given** the CritiqueReport has findings
**When** CritiqueFinding components render
**Then** each finding shows a severity badge (10px uppercase: critical red, warning amber, suggestion green)
**And** expandable accordion reveals evidence + suggested fix

**Given** the Architect's decision rationale
**When** rendered
**Then** user can see why this framework, why these tools, why this grouping

**Given** tool names appear in spec cards
**When** hovered
**Then** a tooltip shows the tool description

**Given** the user clicks Approve
**When** processed
**Then** POST `/sessions/{id}/approve` with `{"checkpoint": "spec", "approved": true}`
**And** pipeline state updates `spec_approved = true`
**And** pipeline resumes to Builder node
**And** phase divider "Building" appears
**And** toast: "Blueprint approved — building your agents..." (3s)
**And** progress messaging: "Designing your agent architecture..." not "Running architect node"

**Given** the user provides free-text feedback instead
**When** submitted
**Then** `control.user_input` message triggers Architect revision with user feedback
**And** revised spec goes through Critic again

**Covers:** FR27-30, UX-DR10-14, UX-DR32-33

---

## Epic 3: Code Generation, Testing & Delivery

A user can receive working, tested agent code as a downloadable zip, with build progress visible in real-time and the system learning from each build to improve future ones.

### Story 3.1: Builder Agent — CrewAI & LangGraph Compilers

As a **system**,
I want the Builder to compile a validated AgentSpec into framework-idiomatic code using Jinja2 templates,
So that generated code follows framework conventions and uses pre-validated tool implementations.

**Acceptance Criteria:**

**Given** a validated AgentSpec with `framework == "crewai"`
**When** the Builder compiles
**Then** it renders Jinja2 templates from `templates/crewai/*.j2`
**And** generates: main.py, agents.py, tools.py, orchestration.py (Crew definition), config.yaml, requirements.txt
**And** code follows CrewAI conventions: Agent, Tool, Crew definitions

**Given** a validated AgentSpec with `framework == "langgraph"`
**When** the Builder compiles
**Then** it renders Jinja2 templates from `templates/langgraph/*.j2`
**And** generates: main.py, agents.py, tools.py, orchestration.py (StateGraph definition), config.yaml, requirements.txt
**And** code follows LangGraph conventions: StateGraph, node functions, conditional edges

**Given** tools referenced in the spec
**When** the Builder generates tool code
**Then** it uses `code_template` from each ToolSchema in the Tool Library
**And** templates are populated with agent-specific parameters

**Given** the generated project
**When** config.yaml is created
**Then** the OpenRouter API key is injected as a config field (not hardcoded in source)
**And** a README.md is generated with usage instructions, config field descriptions, and run command

**Given** the CodeBundle is produced
**When** written to state
**Then** `state["code"]` contains: files dict, framework string, entry_point, dependencies list

**Given** the LLM service is called
**When** the call is for the Builder
**Then** it routes to `anthropic/claude-sonnet-4-6` via OpenRouter

**Covers:** FR31-34, FR36, FR58

---

### Story 3.2: Builder Agent — Code Validation & Self-Retry

As a **system**,
I want the Builder to validate generated code for syntax, imports, and schema compliance before sending to the Tester,
So that obvious errors are caught cheaply without wasting a test execution cycle.

**Acceptance Criteria:**

**Given** a generated CodeBundle
**When** the Builder runs validation
**Then** it performs 3 checks:
1. **Syntax check**: `py_compile.compile()` on each .py file — catches SyntaxError
2. **Import resolution**: every `import` / `from X import Y` is resolvable against the generated requirements.txt + stdlib
3. **Schema check**: function signatures in generated code match the spec's I/O contracts (input/output field names and types)

**Given** validation finds errors
**When** errors are detected
**Then** `code.validation_passed = false` and `code.validation_errors` lists each error with file and line
**And** the Builder attempts self-repair: re-generates only the failing files
**And** re-validates after repair

**Given** validation passes
**When** all 3 checks succeed
**Then** `code.validation_passed = true` and `code.validation_errors` is empty
**And** files are written to `generated_agents/{session_id}/`

**Covers:** FR35

---

### Story 3.3: Tester Agent — Execution & Failure Tracing

As a **system**,
I want the Tester to run generated code in a subprocess, validate output, and trace failures back to root causes,
So that code-level bugs are fixed by the Builder and spec-level issues are recorded for learning.

**Acceptance Criteria:**

**Given** validated code exists in `generated_agents/{session_id}/`
**When** the Tester generates test cases
**Then** test cases are derived from spec I/O contracts: expected output schemas, field presence, quality checks
**And** synthetic test input data is generated based on domain knowledge from RequirementsDoc

**Given** test cases are ready
**When** the Tester executes the generated agent
**Then** it runs via `subprocess.run()` with configurable timeout (default 60s via DOCKER_TIMEOUT config)
**And** captures stdout, stderr, and exit code

**Given** execution completes
**When** the Tester validates output
**Then** it checks: exit code == 0, output matches expected schema, quality criteria met
**And** produces a TestReport with per-test pass/fail, overall pass rate, generated output samples

**Given** a test fails
**When** the Tester traces the failure
**Then** it produces a FailureTrace: failing_agent, error_type (crash/wrong_output/missing_field/quality_fail), root_cause_level (code/spec), suggested_fix
**And** stderr and stdout excerpts are included as evidence

**Given** the TestReport is produced
**When** `route_after_test` evaluates it
**Then** if failures exist with `root_cause_level == "code"` and iteration < MAX_BUILD_ITERATIONS: route back to Builder with FailureTraces
**Then** if all tests pass: route to Learner
**Then** if max iterations reached: route to Learner with partial_success flag

**Given** spec-level failures
**When** detected
**Then** they route to Learner with `partial_success` flag (not back to Architect for MVP)

**Given** the LLM service is called
**When** the call is for the Tester
**Then** it routes to `openai/gpt-4o-mini` via OpenRouter

**Covers:** FR37-45

---

### Story 3.4: Learner Agent & Build Memory

As a **system**,
I want the Learner to structure build outcomes and write them to Chroma for future RAG retrieval,
So that future builds benefit from past successes and avoid repeated failures.

**Acceptance Criteria:**

**Given** the pipeline reaches the Learner node
**When** the Learner processes the build
**Then** it structures a BuildOutcome: requirements_hash, requirements_summary, domain, spec_snapshot, framework_used, tools_used, iterations_needed, test_results, success_patterns, failure_patterns, anti_patterns, lessons_learned, outcome (success/partial_success/failure)

**Given** a structured BuildOutcome
**When** the Learner writes to Chroma
**Then** it calls `store_spec_pattern(spec_id, requirements_summary, metadata)` — for future Architect RAG
**And** if failure_patterns exist: calls `store_anti_pattern(pattern_id, description, metadata)` — for future anti-pattern checks
**And** if domain insights emerge: calls `store_domain_insight(insight_id, insight, metadata)` — for future Elicitor domain context

**Given** tools were used in the build
**When** the Learner evaluates tool performance
**Then** it calls `update_tool_compatibility(tool_id, compatible, incompatible)` based on observed successes/failures

**Given** the LLM service is called
**When** the call is for the Learner
**Then** it routes to `openai/gpt-4o-mini` via OpenRouter

**Given** the Learner completes
**When** the pipeline transitions
**Then** it routes to the completion/delivery node (END)

**Covers:** FR46-48

---

### Story 3.5: Build Progress, Completion & Download

As a **user**,
I want to see real-time build progress and download my working agent project when complete,
So that I know what's happening and can get my agents immediately.

**Acceptance Criteria:**

**Given** the pipeline enters the build phase (after spec approval)
**When** stages execute
**Then** `status.stage_update` messages are sent via status WebSocket for each stage transition
**And** the ProgressTracker component renders: header (18px), progress bar (4px, amber fill, 400ms transition), stage rows with icons (32px) and timing

**Given** the Builder/Tester loop is executing
**When** iterations occur
**Then** progress messaging uses plain language: "Building your agents..." / "Testing the agents..." / "Refining the code..."
**And** never "error/retry" — iteration framed as "refining/improving"

**Given** all tests pass (success)
**When** the CompletionCard renders
**Then** it shows: 64px green checkmark circle, "Your agents are ready." (22px, weight 600), summary table (agents count, framework, test pass count, build time, file count), amber "Download Agent Project" button
**And** staggered fade-up entry animation

**Given** max iterations reached with remaining failures (partial success)
**When** the CompletionCard renders
**Then** it shows: amber checkmark (not green), subtitle "mostly ready", amber test count showing partial pass rate, download still available
**And** warnings about what failed and why

**Given** the user clicks "Download Agent Project"
**When** processed
**Then** GET `/sessions/{id}/download` returns a zip of `generated_agents/{session_id}/`
**And** download initiates within 3 seconds of build completion

**Given** a pipeline stage fails (LLM error, unexpected crash)
**When** the error occurs
**Then** an `error.pipeline_failure` or `error.llm_failure` message is sent
**And** the frontend displays clear, plain-language error messaging (never raw errors or stack traces)
**And** `{type: "error", payload: {stage, message, recoverable}}` format

**Given** a toast notification system
**When** stages complete
**Then** toast appears (auto-dismiss 3s) for stage completion and download ready

**Covers:** FR60-62, FR64, UX-DR15-16, UX-DR29, UX-DR31, UX-DR33

---
