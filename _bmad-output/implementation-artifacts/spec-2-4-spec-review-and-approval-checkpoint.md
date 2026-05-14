---
title: 'Story 2.4: Spec Review & Approval Checkpoint -- Frontend'
type: 'feature'
created: '2026-05-14'
status: 'done'
baseline_commit: 'e6d7479'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
---

<frozen-after-approval reason="human-owned intent -- do not modify unless human renegotiates">

## Intent

**Problem:** Backend sends spec checkpoint data (AgentSpec + CritiqueReport) over WebSocket but the frontend has zero UI to display it. ChatThread only handles `checkpoint_type === "requirements"` -- spec checkpoints are silently ignored. Users cannot review, approve, or provide feedback on the agent blueprint.

**Approach:** Build three new chat components (SpecReviewCard, FlowDiagram, CritiqueFindingList) and wire them into ChatThread alongside an approve/feedback flow that mirrors the existing RequirementsCard pattern from Story 1.4. Add TypeScript types for AgentSpec and CritiqueReport models.

## Boundaries & Constraints

**Always:**
- Follow existing patterns: same button styles (amber primary, outline secondary), same collapse-on-approve animation, same PhaseDivider pattern
- All spec review content renders inline in the chat thread (no modals, no separate pages)
- Spec review container uses `max-w-[840px]` (wider than chat's 720px for visual emphasis)
- Tool badge labels show human-readable tool name, not internal ID or library_ref
- Tool badges use monospace font
- Severity colors: critical = red (`text-red-400`/`bg-red-500/20`), warning = amber (`text-amber-400`/`bg-amber-500/20`), suggestion = green (`text-green-400`/`bg-green-500/20`)
- Respect `prefers-reduced-motion`: disable all animations (stagger, fade-up, badge slide-in) when set

**Ask First:**
- Adding any third-party charting/graph library for FlowDiagram (use CSS flex/grid instead)
- Changing backend WebSocket message shape

**Never:**
- External graph rendering libraries (D3, Mermaid, ReactFlow)
- New REST endpoints (approve endpoint already exists)
- Modifying backend agent logic

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Spec checkpoint arrives | `chat.checkpoint` with `checkpoint_type: "spec"` | PhaseDivider "Your Blueprint" + SpecReviewCard + FlowDiagram + CritiqueFindingList render | N/A |
| Empty agents list | `spec.agents: []` | SpecReviewCard shows "No agents defined" message | N/A |
| No critique findings | `critique.findings: []` | CritiqueFindingList not rendered | N/A |
| No execution_flow.graph | `execution_flow.pattern: "sequential"`, no graph edges | FlowDiagram infers linear chain from agents list order | N/A |
| User approves spec | Click "Approve Blueprint" | POST approve, collapse card, PhaseDivider "Building", toast 3s | Show error toast on POST failure, re-enable button |
| User sends feedback | Type feedback + submit | POST with `approved: false, feedback: text` | Show error toast on POST failure |
| Approve POST fails | Network error or 5xx | Toast "Failed to approve -- try again", button re-enabled | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/types/models.ts` -- add AgentSpec, CritiqueReport, Finding TypeScript types
- `frontend/src/chat-components/SpecReviewCard.tsx` -- new: agent cards grid + rationale + approve/feedback buttons
- `frontend/src/chat-components/FlowDiagram.tsx` -- new: horizontal directed graph of agent execution flow
- `frontend/src/chat-components/CritiqueFindingList.tsx` -- new: severity-badged findings with expandable detail
- `frontend/src/chat-components/ChatThread.tsx` -- wire spec checkpoint rendering (mirror requirements checkpoint pattern)
- `frontend/src/chat-components/RequirementsCard.tsx` -- reference only (pattern to follow)

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/types/models.ts` -- add AgentSpec model types (AgentDef, ToolRef, ExecutionFlow, GraphEdge, SpecMetadata) and CritiqueReport types (Finding, CritiqueReport) -- mirrors backend Pydantic models
- [x] `frontend/src/chat-components/SpecReviewCard.tsx` -- create component: container `max-w-[840px]`. Title "Your Agent Blueprint", decision rationale block, agent cards in grid layout (`repeat(auto-fit, minmax(240px, 1fr))`), each card shows role (14px/600), description (13px/secondary), tool badges (monospace, human-readable name, `title` attr for description). Card hover: border lightens. Approve/Request Changes buttons. Collapse + green flash on approve. Feedback textarea on edit (placeholder: "Describe what you'd like changed in the blueprint..."). Staggered fade-up animation (250ms, 50ms stagger). Respect `prefers-reduced-motion`
- [x] `frontend/src/chat-components/FlowDiagram.tsx` -- create component: reads `execution_flow` and `agents` list. If graph pattern with edges, render nodes + arrows + condition labels. If sequential, chain agents in order. Nodes are rounded rectangles (surface-elevated, 8px radius). Node hover: border turns accent color. Arrows use unicode arrow character. Horizontal flex layout, overflow-x auto
- [x] `frontend/src/chat-components/CritiqueFindingList.tsx` -- create component: maps findings to expandable items. Severity badge (10px uppercase, colored bg) with slide-in animation (4px translate-x, 200ms ease-out). Click to expand/collapse accordion showing evidence + suggested_fix. 8px gap between items. Auto-expand first critical finding if present
- [x] `frontend/src/chat-components/ChatThread.tsx` -- add `else if` branch for `checkpoint_type === "spec"` in the checkpoint rendering block. Render PhaseDivider "Your Blueprint" + SpecReviewCard + FlowDiagram + CritiqueFindingList. Wire approve/feedback handlers calling `approveCheckpoint(sessionId, "spec", ...)`. Deduplicate PhaseDivider on re-renders

**Acceptance Criteria:**
- Given a `chat.checkpoint` message with `checkpoint_type: "spec"`, when ChatThread renders, then PhaseDivider "Your Blueprint" appears followed by SpecReviewCard, FlowDiagram, and CritiqueFindingList
- Given the user clicks "Approve Blueprint", when the POST succeeds, then the spec review content collapses with green border flash, PhaseDivider "Building" appears, and toast "Blueprint approved -- building your agents..." shows for 3 seconds
- Given the user clicks "Request Changes" and submits feedback, when the POST returns, then `approveCheckpoint` is called with `approved: false` and the feedback text
- Given critique findings with mixed severities, when CritiqueFindingList renders, then critical findings show red badges, warnings show amber, suggestions show green

## Design Notes

**SpecReviewCard structure (top to bottom):**
1. Title: "Your Agent Blueprint" (15px, weight 600)
2. Rationale block: italic text showing `architect_reasoning` (13px, tertiary, border-l-2 accent)
3. Agent cards grid
4. FlowDiagram (separate component, rendered below cards)
5. CritiqueFindingList (separate component, rendered below diagram)
6. Action buttons (Approve Blueprint / Request Changes)

**Tool tooltip pattern:** Use `title` attribute on tool badge spans for hover tooltip. Simple, no library needed.

**Stagger animation:** Use inline `style={{ animationDelay: \`${i * 50}ms\` }}` on each agent card with a shared `animate-[fadeUp_250ms_ease-out_both]` class.

## Verification

**Commands:**
- `cd frontend && npx tsc --noEmit` -- expected: no type errors
- `cd frontend && npm run build` -- expected: builds successfully

**Manual checks:**
- Send mock `chat.checkpoint` with `checkpoint_type: "spec"` via WebSocket -- verify all three components render
- Click Approve -- verify collapse animation, PhaseDivider "Building", toast
- Click Request Changes -- verify textarea appears, submit sends feedback
- Verify agent cards grid wraps correctly at different widths
- Verify FlowDiagram scrolls horizontally for many agents

## Suggested Review Order

**Spec checkpoint wiring (entry point)**

- ChatThread now routes `checkpoint_type: "spec"` to SpecReviewCard with approve/feedback handlers
  [`ChatThread.tsx:106`](../../frontend/src/chat-components/ChatThread.tsx#L106)

- Approve and feedback callbacks mirror requirements pattern, call existing REST endpoint
  [`ChatThread.tsx:55`](../../frontend/src/chat-components/ChatThread.tsx#L55)

**Agent blueprint display**

- SpecReviewCard: rationale block, agent card grid, nested FlowDiagram + CritiqueFindingList, collapse-on-approve
  [`SpecReviewCard.tsx:15`](../../frontend/src/chat-components/SpecReviewCard.tsx#L15)

- AgentCard sub-component: role/goal/tool badges with hover and stagger animation
  [`SpecReviewCard.tsx:139`](../../frontend/src/chat-components/SpecReviewCard.tsx#L139)

**Execution flow visualization**

- FlowDiagram: topological sort for node order, edge resolution from graph/sends_to/sequential fallback
  [`FlowDiagram.tsx:28`](../../frontend/src/chat-components/FlowDiagram.tsx#L28)

**Critique findings**

- CritiqueFindingList: severity badges with slide-in, expandable accordion, auto-expand first critical
  [`CritiqueFindingList.tsx:19`](../../frontend/src/chat-components/CritiqueFindingList.tsx#L19)

**Supporting types and styles**

- AgentSpec + CritiqueReport TypeScript types mirroring backend Pydantic models
  [`models.ts:37`](../../frontend/src/types/models.ts#L37)

- slideIn keyframe for critique badge animation
  [`index.css:99`](../../frontend/src/index.css#L99)
