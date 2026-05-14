# Epic 2 Context: Architecture Generation & Adversarial Review

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Transform approved requirements into a thoughtfully designed, adversarially-reviewed agent architecture blueprint that users can understand, trust, and control. The spec review checkpoint is the "trust moment" -- where users see their workflow translated into a visual agent design and decide whether to proceed to code generation.

## Stories

- Story 2.1: Architect Agent -- RAG Queries & Task Decomposition
- Story 2.2: Architect Agent -- Spec Compilation
- Story 2.3: Critic Agent & Architect-Critic Feedback Loop
- Story 2.4: Spec Review & Approval Checkpoint

## Requirements & Constraints

- Architect uses claude-sonnet-4-6; Critic uses gpt-4o (cross-model adversarial review by design)
- Architect follows 7-step process: task decomposition, tool selection, agent grouping, flow design, memory design, error handling, I/O contracts
- Critic runs 5 programmatic checks (circular deps, format compat, dependency completeness, dead-ends, resource conflicts) plus 1 LLM semantic review
- Critical findings loop back to Architect for revision; max 3 iterations before forcing to checkpoint
- Human checkpoint 2 pauses pipeline via LangGraph `interrupt()` with AgentSpec + CritiqueReport payload
- User can approve (resumes to Builder) or provide free-text feedback (triggers Architect revision + re-Critic)
- Spec review UI must translate technical architecture into plain-language visual components -- agent cards, flow diagram, critique badges
- All tool references must match Tool Schema Library IDs
- Pipeline state: `spec`, `critique`, `architect_reasoning`, `spec_approved`, `spec_iteration`

## Technical Decisions

- LangGraph StateGraph with `interrupt()` for checkpoints, `Command(resume=...)` for approval
- AgentSpec Pydantic model: metadata, agents, tools, memory, execution_flow, error_handling, io_contracts
- CritiqueReport model: findings (vector, severity, description, location, evidence, suggested_fix), summary, iteration
- Feedback injected as critical Finding so Architect addresses it in revision mode
- Approve endpoint: POST `/sessions/{id}/approve` with `{"checkpoint": "spec", "approved": true}`
- Frontend WebSocket receives `chat.checkpoint` with `checkpoint_type: "spec"`
- Same approve/edit pattern as requirements checkpoint (Story 1.4) but with richer visual rendering

## UX & Interaction Patterns

- Spec review is embedded in chat thread (conversation IS the interface)
- AgentSpecCard: role name (14px, weight 600), description (13px, secondary), tool tags as monospace badges. Grid layout: `repeat(auto-fit, minmax(240px, 1fr))`. Staggered fade-up 250ms, 50ms between cards
- FlowDiagram: horizontal directed graph, rounded-rectangle nodes (surface-elevated, 8px radius), arrow connectors with condition labels (11px)
- CritiqueFinding: severity badge (10px uppercase -- critical red, warning amber, suggestion green), expandable accordion for evidence + suggested fix
- Decision rationale visible to user (why framework, tools, grouping)
- Tool tooltips on hover
- PhaseDivider "Your Blueprint" before spec content
- On approve: PhaseDivider "Building", toast "Blueprint approved -- building your agents..." (3s)
- Spec cards max width 840px (wider than chat messages for visual emphasis)
- Button pattern matches Story 1.4: amber primary Approve, outline secondary Request Changes

## Cross-Story Dependencies

- Story 2.1-2.3 must be complete (Architect + Critic produce AgentSpec + CritiqueReport)
- Story 1.4 establishes checkpoint UI pattern (RequirementsCard, approve flow, PhaseDivider)
- Story 3.1 (Builder) receives the approved spec -- depends on 2.4 approval flow working
