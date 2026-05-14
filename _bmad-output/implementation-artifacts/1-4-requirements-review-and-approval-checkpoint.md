# Story 1.4: Requirements Review & Approval Checkpoint

## Status: review

## Story

As a **user**,
I want to review the structured requirements document and approve or correct it,
So that I'm confident the system understood my needs before it starts designing.

## Acceptance Criteria (ACs)

### AC1: Pipeline Pauses and Sends Checkpoint on RequirementsDoc Completion

**Given** the Elicitor produces a fully compiled RequirementsDoc (all categories scored >= 0.7 or max 3 rounds reached),
**When** the pipeline transitions to the `human_review_requirements` node,
**Then** pipeline execution pauses (LangGraph interrupt),
**And** the backend sends a `chat.checkpoint` message over the chat WebSocket (`/ws/chat/{session_id}`) with the full RequirementsDoc as payload,
**And** the backend sends a `status.stage_update` message over the status WebSocket (`/ws/status/{session_id}`) with `is_checkpoint: true` and `stage: "requirements_review"`.

### AC2: RequirementsCard Renders Correctly

**Given** the `chat.checkpoint` message with `checkpoint_type: "requirements"` arrives at the frontend,
**When** the RequirementsCard component renders,
**Then** it displays the title "Here's what I understood — does this look right?",
**And** each field from the RequirementsDoc is rendered as a key-value row (bold label on the left, description text on the right),
**And** an Approve button appears on the left (amber primary: `bg-amber-500`, dark text, weight 600),
**And** an Edit button appears on the right (outline secondary: transparent background, `border border-[#2e2e2e]`, weight 500),
**And** at most one primary (amber) button is visible at any time (UX-DR20).

### AC3: Approve Flow — Backend Processes Approval

**Given** the frontend calls `POST /sessions/{session_id}/approve` with body `{"checkpoint": "requirements", "approved": true}`,
**When** the endpoint handler processes the request,
**Then** the pipeline state field `requirements_approved` is set to `true`,
**And** the paused LangGraph graph execution is resumed (pipeline continues to the `architect` node),
**And** the endpoint returns `{"status": "resumed"}`.

### AC4: Approve Flow — Frontend Feedback

**Given** the user clicks the Approve button,
**When** the POST to `/sessions/{session_id}/approve` succeeds,
**Then** the RequirementsCard collapses (height animates to 0 over 300ms) and a green border flash (300ms, `border-green-500`) is shown before removal,
**And** a system `chat.message` arrives in the chat thread with text "Requirements approved — designing your agent architecture...",
**And** a shadcn/ui Toast notification appears with content "Requirements approved" and auto-dismisses after 3 seconds (UX-DR31),
**And** the pipeline sidebar transitions the "Requirements Review" stage dot to green checkmark and the "Architecture" stage dot to amber pulsing (active).

### AC5: Edit Flow — Corrections Sent and Elicitor Re-runs

**Given** the user clicks the Edit button and types free-text corrections in the input field that appears,
**When** the user submits the correction,
**Then** a `control.user_input` WebSocket message is sent over the chat WebSocket with the correction text as payload,
**And** the Elicitor agent incorporates the corrections into the RequirementsDoc,
**And** a new `chat.checkpoint` message is sent to the frontend with the updated RequirementsDoc,
**And** the RequirementsCard is re-rendered with the updated content for re-review,
**And** `requirements_approved` remains `false` in pipeline state.

### AC6: PhaseDivider Renders on Transition

**Given** the pipeline transitions from the elicitation phase to the requirements review phase,
**When** the RequirementsCard is about to be rendered in the chat thread,
**Then** a PhaseDivider component appears immediately above it with the label "Requirements Summary" (11px, uppercase, letter-spacing 0.05em, tertiary text color),
**And** the PhaseDivider fades in over 400ms (UX-DR17, UX-DR30).

---

## Technical Implementation Notes

### Architecture

This story touches the pipeline layer (backend), the REST API (backend), and the chat UI (frontend). It has no new agent logic — the Elicitor from Story 1.3 is already complete. This story wires the output of the Elicitor to the human review checkpoint and implements the full approve/edit interaction loop.

**Files created or modified:**

| File | Action | Purpose |
|---|---|---|
| `backend/app/pipeline/graph.py` | Modify | Add `human_review_requirements` node, edge from `elicitor` to it, edge from it to `architect` |
| `backend/app/pipeline/checkpoints.py` | Create | `human_checkpoint_1()` node function — sends WS messages, pauses, handles resume |
| `backend/app/main.py` | Modify | Add `POST /sessions/{session_id}/approve` endpoint |
| `backend/app/models/messages.py` | Modify | Add `CheckpointMessage`, `ControlMessage` types if not already present (from Story 1.1) |
| `frontend/src/components/RequirementsCard.tsx` | Modify | Full implementation — stubbed in Story 1.2 |
| `frontend/src/components/PhaseDivider.tsx` | Already exists (Story 1.2) | No changes needed unless label prop is missing |
| `frontend/src/hooks/useWebSocket.ts` | Modify | Handle `chat.checkpoint` message type, dispatch to reducer |
| `frontend/src/context/AppContext.tsx` | Modify | Add `CHECKPOINT_ARRIVED` and `REQUIREMENTS_APPROVED` actions to reducer |
| `frontend/src/api/sessions.ts` | Create or modify | `approveCheckpoint()` REST call wrapper |
| `frontend/src/types/messages.ts` | Modify | Add `CheckpointMessage` type mirroring backend |

**Dependency chain:**
- Story 1.1: WebSocket endpoints, `POST /sessions/{id}/approve` REST shape, message type enums — must be complete
- Story 1.2: Chat UI, `PhaseDivider`, reducer skeleton, `useWebSocket` hook — must be complete
- Story 1.3: Elicitor produces `RequirementsDoc` in pipeline state — must be complete

---

### Backend Implementation

#### 1. Checkpoint Node Function

Create `backend/app/pipeline/checkpoints.py`:

```python
import asyncio
import logging
from typing import Any
from langgraph.types import interrupt

from app.models.state import FrankensteinState
from app.models.messages import CheckpointMessage, StageUpdateMessage
from app.services.websocket_manager import ws_manager  # injected singleton

logger = logging.getLogger(__name__)


async def human_checkpoint_1(state: FrankensteinState) -> dict[str, Any]:
    """
    LangGraph node: pauses execution after Elicitor completes.
    Sends RequirementsDoc to frontend via chat WebSocket.
    Sends stage_update with checkpoint indicator via status WebSocket.
    Uses LangGraph interrupt() to pause. On resume, returns with
    requirements_approved set by the approve endpoint.
    """
    session_id = state["session_id"]
    requirements = state["requirements"]

    # Build checkpoint message payload
    checkpoint_msg = CheckpointMessage(
        type="chat.checkpoint",
        session_id=session_id,
        payload={
            "checkpoint_type": "requirements",
            "requirements": requirements.model_dump(),
        },
    )

    # Build status update payload
    status_msg = StageUpdateMessage(
        type="status.stage_update",
        session_id=session_id,
        payload={
            "stage": "requirements_review",
            "status": "active",
            "description": "Reviewing requirements",
            "is_checkpoint": True,
        },
    )

    # Send both WS messages before pausing
    await ws_manager.send_chat(session_id, checkpoint_msg.model_dump())
    await ws_manager.send_status(session_id, status_msg.model_dump())

    logger.info(f"[{session_id}] Checkpoint 1 reached — pipeline paused for human review")

    # LangGraph interrupt: pauses execution here.
    # The approve endpoint resumes by calling graph.invoke() with updated state.
    interrupt("requirements_review")

    # Execution resumes here after approval — state has been updated externally.
    return {}
```

**Important:** The node returns an empty dict after the interrupt is resolved. The state update (`requirements_approved = True`) is injected by the resume call from the approve endpoint, not by this node.

#### 2. Graph Wiring

In `backend/app/pipeline/graph.py`, add the checkpoint node and edges:

```python
from app.pipeline.checkpoints import human_checkpoint_1

graph.add_node("human_review_requirements", human_checkpoint_1)

# Wire: elicitor -> checkpoint -> architect
graph.add_edge("elicitor", "human_review_requirements")
graph.add_edge("human_review_requirements", "architect")
```

The graph definition after this story's changes (relevant section):

```
START → elicitor → human_review_requirements → architect → ...
```

For the edit flow (correction loop back to elicitor), the conditional routing from `human_review_requirements` is handled by the approve endpoint directly — it sends corrections back through the Elicitor re-run path, not via a separate graph edge. See the approve endpoint below.

#### 3. Approve Endpoint

Add to `backend/app/main.py`:

```python
from pydantic import BaseModel
from typing import Literal

class ApproveRequest(BaseModel):
    checkpoint: Literal["requirements", "spec"]
    approved: bool
    feedback: str | None = None  # free-text corrections if not approved

class ApproveResponse(BaseModel):
    status: Literal["resumed", "revision_requested"]


@app.post("/sessions/{session_id}/approve", response_model=ApproveResponse)
async def approve_checkpoint(session_id: str, body: ApproveRequest):
    session = session_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if body.checkpoint != "requirements":
        raise HTTPException(status_code=400, detail="Invalid checkpoint for this endpoint. Use 'requirements' or 'spec'.")

    if body.approved:
        # Update state and resume the paused graph
        await session.pipeline.resume(
            state_update={"requirements_approved": True}
        )
        logger.info(f"[{session_id}] Requirements approved — pipeline resuming to architect")

        # Send confirmation chat message to frontend
        await ws_manager.send_chat(session_id, {
            "type": "chat.message",
            "session_id": session_id,
            "payload": {
                "role": "system",
                "content": "Requirements approved — designing your agent architecture...",
            },
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Update stage indicator
        await ws_manager.send_status(session_id, {
            "type": "status.stage_update",
            "session_id": session_id,
            "payload": {
                "stage": "requirements_review",
                "status": "done",
                "is_checkpoint": False,
            },
            "timestamp": datetime.utcnow().isoformat(),
        })

        return ApproveResponse(status="resumed")

    else:
        # Edit flow: send feedback back through Elicitor for correction
        # The pipeline stays paused; the Elicitor re-runs with corrections injected
        await session.pipeline.inject_correction(
            corrections=body.feedback or "",
            target_node="elicitor",
        )
        logger.info(f"[{session_id}] Requirements sent back to Elicitor with corrections")
        return ApproveResponse(status="revision_requested")
```

**Session and pipeline resume abstraction:**
The `session.pipeline.resume(state_update)` call is a wrapper around LangGraph's interrupt/resume mechanism. Depending on the LangGraph version used, this may use `graph.invoke()` with a `Command(resume=...)` or `thread_id`-based continuation. The exact LangGraph API call must follow the version pinned in `requirements.txt`. The key contract is: after calling resume with `requirements_approved=True`, the graph continues from `human_review_requirements` to `architect`.

**State management for in-memory sessions:**
Since NFR16 specifies in-memory-only session state (no persistence), the pipeline graph runner and session state live in a Python dict keyed by `session_id`. The approve endpoint looks up the running graph task by `session_id` and signals it.

Example in-memory session store pattern:

```python
# In session_service.py
_sessions: dict[str, SessionState] = {}

class SessionState:
    session_id: str
    pipeline_task: asyncio.Task  # the running graph coroutine
    state: FrankensteinState
    checkpoint_event: asyncio.Event  # set by approve endpoint to unblock interrupt
    correction_queue: asyncio.Queue  # for edit corrections
```

The `interrupt()` in the checkpoint node blocks on `checkpoint_event.wait()`. The approve endpoint calls `checkpoint_event.set()` after updating state. This is the recommended pattern for LangGraph human-in-the-loop with FastAPI.

#### 4. Edit (Correction) Flow — Backend

When `approved: false` is received:

1. The `feedback` string is placed in the session's `correction_queue`.
2. The checkpoint node (still running, blocked on interrupt) dequeues the correction.
3. The correction is added to `state["human_answers"]` as a correction entry.
4. The checkpoint node calls `elicitor_agent(state)` directly (sub-invocation) with the correction context.
5. The Elicitor re-runs, produces an updated `RequirementsDoc`.
6. The checkpoint node re-sends `chat.checkpoint` with the updated requirements.
7. The interrupt is re-set, and the cycle repeats.

This edit loop does NOT go back through the graph edges — it loops inside the checkpoint node function itself to keep the graph state clean.

---

### Frontend Implementation

#### RequirementsCard Component

Full implementation at `frontend/src/components/RequirementsCard.tsx`.

**Props:**

```typescript
interface RequirementsCardProps {
  requirements: RequirementsDoc;
  onApprove: () => Promise<void>;
  onEdit: (corrections: string) => void;
  isLoading?: boolean;  // true while POST /approve is in flight
}
```

**RequirementsDoc type** (mirrors backend Pydantic model, defined in `frontend/src/types/models.ts`):

```typescript
interface DataSpec {
  name: string;
  format: string;
  description: string;
  example?: string;
}

interface ProcessStep {
  step_number: number;
  description: string;
  rules: string[];
  depends_on: number[];
}

interface EdgeCase {
  description: string;
  expected_handling: string;
}

interface QualityCriterion {
  criterion: string;
  validation_method: string;
}

interface RequirementsDoc {
  domain: string;
  inputs: DataSpec[];
  outputs: DataSpec[];
  process_steps: ProcessStep[];
  edge_cases: EdgeCase[];
  quality_criteria: QualityCriterion[];
  constraints: string[];
  assumptions: string[];
}
```

**Rendered sections (key-value rows):**

Each top-level RequirementsDoc field is rendered as a labeled section. The label is bold (weight 600, 13px), the value is secondary text (13px). For list fields (inputs, outputs, process_steps, etc.), each list item is rendered as a sub-row.

Section label mapping:

| Field | Display Label |
|---|---|
| domain | Domain |
| inputs | Inputs |
| outputs | Outputs |
| process_steps | Process Steps |
| edge_cases | Edge Cases |
| quality_criteria | Quality Criteria |
| constraints | Constraints |
| assumptions | Assumptions (flagged gaps) |

The `assumptions` section renders with an amber left border (2px) to signal that these are system-inferred, not user-confirmed.

**Button behavior:**

- Approve button: amber background (`bg-amber-500`), dark text (`text-neutral-900`), weight 600, 44px min height (WCAG AA). On click, calls `onApprove()`, then shows loading spinner inside button, button disabled while in-flight.
- Edit button: transparent background, `border border-[#2e2e2e]`, weight 500. On click, renders an inline textarea for corrections (below the requirements rows). Approve button is hidden while edit mode is active (max one primary visible, UX-DR20).
- Press animation: `scale-[0.97]` on `active:`, 100ms transition (UX-DR21).

**Collapse + green border flash on approve:**

```typescript
// After onApprove() resolves:
// 1. Add green border class (border-green-500, 300ms transition)
// 2. After 300ms, begin height collapse (max-h-0, overflow-hidden, 300ms)
// 3. After 600ms total, remove from DOM
```

This is implemented with `useState` controlling a CSS class and a `setTimeout` chain. Respect `prefers-reduced-motion`: if set, skip animations and remove immediately.

**Edit mode inline textarea:**

When Edit is clicked:
- A `<textarea>` appears below the requirement rows with placeholder "Describe what needs to change..."
- A "Submit corrections" button appears (amber primary, replaces Approve in the primary slot)
- On submit, `onEdit(correctionText)` is called, the textarea clears, and a TypingIndicator appears in the chat thread to signal that Elicitor is re-running
- The existing RequirementsCard stays visible (not collapsed) until the re-run completes and a new `chat.checkpoint` arrives

#### PhaseDivider Integration

The `PhaseDivider` component (from Story 1.2) is rendered in the chat thread reducer when a `chat.checkpoint` message with `checkpoint_type: "requirements"` arrives, immediately before the `RequirementsCard` entry is added to the message list:

```typescript
// In reducer (AppContext.tsx), CHECKPOINT_ARRIVED action:
case "CHECKPOINT_ARRIVED": {
  if (action.payload.checkpoint_type === "requirements") {
    return {
      ...state,
      messages: [
        ...state.messages,
        { type: "phase_divider", label: "Requirements Summary", id: uuid() },
        { type: "checkpoint", ...action.payload, id: uuid() },
      ],
      checkpointPending: true,
    };
  }
  // ... spec checkpoint handling in Story 2.x
}
```

The chat thread renderer maps `type: "phase_divider"` to `<PhaseDivider label={message.label} />` with the 400ms fade-in CSS animation.

#### WebSocket Handling

In `frontend/src/hooks/useWebSocket.ts`, add handling for `chat.checkpoint`:

```typescript
// In the chat WS onmessage handler:
if (msg.type === "chat.checkpoint") {
  dispatch({ type: "CHECKPOINT_ARRIVED", payload: msg.payload });
}
```

The existing handler for `status.stage_update` (from Story 1.1/1.2) already handles the sidebar stage indicator update — no new logic needed there, only the `is_checkpoint: true` flag needs to be passed through to the `StageIndicator` component to render a pause/review visual state.

#### REST Call Wrapper

`frontend/src/api/sessions.ts`:

```typescript
export async function approveCheckpoint(
  sessionId: string,
  checkpoint: "requirements" | "spec",
  approved: boolean,
  feedback?: string
): Promise<{ status: "resumed" | "revision_requested" }> {
  const res = await fetch(`/api/sessions/${sessionId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ checkpoint, approved, feedback: feedback ?? null }),
  });
  if (!res.ok) {
    throw new Error(`Approve request failed: ${res.status}`);
  }
  return res.json();
}
```

---

### WebSocket Flow

#### Full Message Sequence — Approve Flow

```
Backend (Elicitor completes)
  │
  ├─► [chat WS] chat.checkpoint { checkpoint_type: "requirements", requirements: {...} }
  │       Frontend: dispatch CHECKPOINT_ARRIVED → renders PhaseDivider + RequirementsCard
  │
  └─► [status WS] status.stage_update { stage: "requirements_review", status: "active", is_checkpoint: true }
          Frontend: sidebar stage dot → amber (active)

User clicks "Approve"
  │
  └─► [REST] POST /sessions/{id}/approve { checkpoint: "requirements", approved: true }
          Backend: sets requirements_approved=true, resumes graph
          │
          ├─► [chat WS] chat.message { role: "system", content: "Requirements approved — designing your agent architecture..." }
          │       Frontend: new ChatMessage appears in thread
          │
          └─► [status WS] status.stage_update { stage: "requirements_review", status: "done" }
                  Frontend: sidebar stage dot → green checkmark
                  Next: sidebar "Architecture" stage → amber pulsing
```

#### Full Message Sequence — Edit Flow

```
User clicks "Edit" → types corrections → clicks "Submit corrections"
  │
  └─► [chat WS] control.user_input { content: "The inputs should also include..." }
          Frontend: shows TypingIndicator
          Backend: receives correction, re-runs Elicitor
          │
          └─► [chat WS] chat.checkpoint { checkpoint_type: "requirements", requirements: { ...updated... } }
                  Frontend: renders new RequirementsCard (replaces or appends — see State Management)
                  requirements_approved stays false
```

**Note on duplicate PhaseDivider:** On an edit re-run, do NOT re-render the PhaseDivider. The reducer should check if a `phase_divider` with label "Requirements Summary" is already in the message list before inserting another. If present, only append the new `checkpoint` message.

---

### State Management

All frontend state lives in React context + useReducer (`AppContext.tsx` from Story 1.2). No external state library (UX-DR24).

#### Relevant State Shape (additions for this story)

```typescript
interface AppState {
  // ... existing fields from Stories 1.1-1.3 ...
  checkpointPending: boolean;       // true while requirements or spec checkpoint is awaiting approval
  approvalInFlight: boolean;        // true while POST /approve is in flight (disables Approve button)
  editMode: boolean;                // true when user clicked Edit in RequirementsCard
  latestRequirements: RequirementsDoc | null;  // most recent RequirementsDoc from checkpoint
}
```

#### New Actions

```typescript
type Action =
  | { type: "CHECKPOINT_ARRIVED"; payload: { checkpoint_type: string; requirements: RequirementsDoc } }
  | { type: "APPROVAL_STARTED" }        // POST in flight — disable button
  | { type: "APPROVAL_SUCCEEDED" }      // POST returned "resumed"
  | { type: "APPROVAL_FAILED"; error: string }
  | { type: "EDIT_MODE_ENTERED" }
  | { type: "EDIT_MODE_EXITED" }
  | { type: "CORRECTION_SUBMITTED"; corrections: string }
```

#### Reducer Logic

```typescript
case "CHECKPOINT_ARRIVED":
  // Insert PhaseDivider (only if not already present) + checkpoint message
  // Set checkpointPending = true, latestRequirements = payload.requirements

case "APPROVAL_STARTED":
  // Set approvalInFlight = true

case "APPROVAL_SUCCEEDED":
  // Set checkpointPending = false, approvalInFlight = false, editMode = false
  // The RequirementsCard collapse animation is handled in the component itself via local state

case "EDIT_MODE_ENTERED":
  // Set editMode = true

case "CORRECTION_SUBMITTED":
  // Set editMode = false, approvalInFlight = true (corrections in-flight)
  // Append TypingIndicator to message list
```

---

### Key Technical Decisions

#### 1. LangGraph Interrupt Pattern vs. Async Event

The checkpoint uses LangGraph's `interrupt()` primitive to genuinely pause the graph rather than polling. This is the correct pattern for human-in-the-loop with LangGraph. The alternative (polling a flag) would require the graph to keep running and check state on each tick, which is both wasteful and architecturally incorrect.

The FastAPI approve endpoint unblocks the interrupt via an `asyncio.Event` stored in the session state. This is the recommended approach for integrating LangGraph interrupts with FastAPI's async event loop.

#### 2. Edit Loop Inside Checkpoint Node (Not Graph Edges)

The correction re-run loops inside `human_checkpoint_1()` rather than using a graph edge back to `elicitor`. This keeps the graph topology simple (no backward edges at this stage) and avoids resetting all Elicitor state. The correction is injected as additional context into the existing Elicitor re-run, not a fresh start.

#### 3. RequirementsCard Collapse via Local State

The card collapse animation on approve is managed by local React component state, not the global reducer. The global reducer only tracks `checkpointPending`. The visual collapse is a local ephemeral effect that does not need to persist in app state.

#### 4. No Separate "Correction" WebSocket Message Type

The edit correction is sent via `control.user_input` (the same type used for general user input in the Elicitor Q&A). This keeps the message type set minimal. The backend distinguishes context (checkpoint vs. Q&A) by checking `state["requirements_approved"]` — if false and the pipeline is paused at the checkpoint, incoming `control.user_input` messages are routed as corrections.

#### 5. Assumptions Section Visual Treatment

If the RequirementsDoc has a non-empty `assumptions` list, these are rendered with an amber left border and a "(System-inferred)" label. This is a trust signal: users see exactly what the system filled in vs. what they explicitly stated. Domain experts will notice and correct wrong assumptions — which is the intent.

#### 6. Toast via shadcn/ui

Use the shadcn/ui Toast component (already installed per design system decision). Call `toast({ title: "Requirements approved", duration: 3000 })` from within the `APPROVAL_SUCCEEDED` handler. No custom toast implementation.

---

## Dev Notes

### Files to Create

- `backend/app/pipeline/checkpoints.py` — New file, contains `human_checkpoint_1()` and later `human_checkpoint_2()`

### Files to Modify

- `backend/app/pipeline/graph.py` — Add node + edges as described above
- `backend/app/main.py` — Add `ApproveRequest`, `ApproveResponse` models and `POST /sessions/{id}/approve` endpoint
- `frontend/src/components/RequirementsCard.tsx` — Full implementation (currently stubbed)
- `frontend/src/context/AppContext.tsx` — Add `CHECKPOINT_ARRIVED`, `APPROVAL_STARTED`, `APPROVAL_SUCCEEDED`, `EDIT_MODE_ENTERED`, `CORRECTION_SUBMITTED` actions and reducer cases
- `frontend/src/hooks/useWebSocket.ts` — Add `chat.checkpoint` message dispatch
- `frontend/src/types/messages.ts` — Add `CheckpointMessage` type
- `frontend/src/types/models.ts` — Add `RequirementsDoc`, `DataSpec`, `ProcessStep`, `EdgeCase`, `QualityCriterion` TypeScript types
- `frontend/src/api/sessions.ts` — Add `approveCheckpoint()` function

### Do Not Touch

- `backend/app/agents/elicitor.py` — Elicitor logic is complete from Story 1.3. This story only wires its output.
- `backend/app/models/requirements.py` — `RequirementsDoc` model is complete from Story 1.2.
- `frontend/src/components/PhaseDivider.tsx` — Already implemented in Story 1.2. Only verify it accepts a `label` prop.

### LangGraph Version Note

Confirm the LangGraph version in `backend/requirements.txt` before implementing the interrupt/resume pattern. LangGraph >= 0.2 uses `interrupt()` from `langgraph.types` and `Command(resume=...)` from `langgraph.types` for resumption. Older versions use a different mechanism. The `backend/requirements.txt` is the source of truth.

### Test Scenarios for Manual Validation

1. **Happy path — approve:** Submit prompt → answer Elicitor questions → RequirementsCard appears → click Approve → card collapses with green flash → toast appears → chat shows "Requirements approved..." message → pipeline sidebar advances to Architecture stage.

2. **Edit path — single correction:** Submit prompt → RequirementsCard appears → click Edit → type correction → submit → TypingIndicator appears → updated RequirementsCard appears (new content) → click Approve → happy path continues.

3. **Edit path — multiple corrections:** Same as above but click Edit on the updated card and correct again. Verify the pipeline stays paused and `requirements_approved` stays false until explicit Approve.

4. **PhaseDivider deduplication:** In the edit path, verify that only ONE "Requirements Summary" PhaseDivider appears in the chat thread regardless of how many RequirementsCard versions are shown.

5. **Reduced motion:** In browser devtools, enable `prefers-reduced-motion`. Verify no animations play (card does not animate collapse, PhaseDivider appears instantly, no scale animations on buttons).

6. **Approve button disabled during in-flight:** Click Approve → verify button shows loading state and is non-interactive until the POST returns.

### Relevant FR Coverage

- FR7: User can review the generated requirements document in a readable rendered format at human checkpoint 1 — covered by AC1 + AC2
- FR8: User can approve the requirements, or provide free-text corrections that the Elicitor incorporates before re-presenting — covered by AC3-AC5
- UX-DR9: RequirementsCard component — covered by AC2
- UX-DR20: Button hierarchy, max one primary — covered by AC2 (RequirementsCard buttons)
- UX-DR30: Phase transition label "Requirements Summary" — covered by AC6
