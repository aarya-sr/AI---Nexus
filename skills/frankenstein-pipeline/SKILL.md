---
name: frankenstein-pipeline
description: Meta-agentic pipeline from prompt to working agent. Use when user says 'build me an agent' or 'start pipeline'.
---

# frankenstein-pipeline

## Overview

This skill orchestrates Frankenstein's six-stage meta-agentic pipeline that transforms a fuzzy natural-language prompt into a tested, deployable multi-agent system (CrewAI or LangGraph). Act as a pipeline orchestrator that splits domain knowledge extraction (human's job) from engineering execution (Frankenstein's job).

Pipeline: Elicit → [Checkpoint] → Architect ↔ Critic → [Checkpoint] → Builder ↔ Tester → Learner. Two feedback loops enable autonomous self-correction: Critic attacks the Architect's spec until no criticals remain, Tester routes failures back to Builder (code-level) or Architect (spec-level). Two human checkpoints gate progression.

Output: a `generated_agent/` directory containing runnable code, plus build learnings stored in Chroma for future RAG retrieval.

## Conventions

- Bare paths (e.g. `references/elicitation.md`) resolve from the skill root.
- `{skill-root}` resolves to this skill's installed directory.
- `{project-root}`-prefixed paths resolve from the project working directory.
- `{skill-name}` resolves to the skill directory's basename.

## On Activation

### Initialize Pipeline State

```python
class FrankensteinState(TypedDict):
    # Stage 1: Elicitor
    raw_prompt: str
    elicitor_questions: list[dict]       # generated questions per category
    human_answers: list[dict]            # human responses
    requirements: RequirementsDoc        # structured output
    requirements_approved: bool          # human checkpoint 1

    # Stage 2-3: Architect + Critic
    tool_library_matches: list[ToolSchema]
    past_spec_matches: list[dict]          # Chroma query results (document + metadata)
    spec: AgentSpec                      # generated specification
    critique: CritiqueReport             # critic findings
    spec_iteration: int                  # architect-critic loop count
    spec_approved: bool                  # human checkpoint 2

    # Stage 4-5: Builder + Tester
    generated_code: CodeBundle           # compiled code output
    test_cases: list[TestCase]           # from spec contracts
    test_results: TestReport             # execution results
    failure_traces: list[FailureTrace]   # mapped to spec decisions
    build_iteration: int                 # build-test loop count

    # Stage 6: Learning
    build_outcome: BuildOutcome          # final record
```

Set initial values: `raw_prompt` from user input, both iteration counters to `0`, both approval flags to `false`, everything else null/empty.

### Pipeline Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| MAX_ELICITOR_ROUNDS | 3 | Max Q&A loops before flagging assumptions |
| MAX_SPEC_ITERATIONS | 3 | Max Architect-Critic loops |
| MAX_BUILD_ITERATIONS | 3 | Max Builder-Tester loops |
| DOCKER_TIMEOUT | 60s | Container kill timeout |

### Model Routing

| Agent | Model | Via |
|-------|-------|-----|
| Elicitor | gpt-4o-mini | OpenRouter |
| Architect | claude-sonnet-4-6 | OpenRouter |
| Critic | gpt-4o | OpenRouter |
| Builder | claude-sonnet-4-6 | OpenRouter |
| Tester | gpt-4o-mini | OpenRouter |
| Learner | gpt-4o-mini | OpenRouter |

Route to Elicitation: load `references/elicitation.md`.

## Stage Routing

| From | To | Condition |
|------|-----|-----------|
| Elicitation | Requirements Checkpoint | RequirementsDoc produced |
| Requirements Checkpoint | Architecture | Human approves |
| Requirements Checkpoint | Elicitation | Human rejects (with feedback) |
| Architecture | Critique | AgentSpec produced |
| Critique | Architecture | criticals > 0 AND spec_iteration < MAX_SPEC_ITERATIONS |
| Critique | Spec Checkpoint | no criticals OR spec_iteration >= MAX_SPEC_ITERATIONS |
| Spec Checkpoint | Build | Human approves |
| Spec Checkpoint | Architecture | Human requests changes (does NOT increment spec_iteration — human feedback is separate from Critic loops) |
| Spec Checkpoint | Requirements Checkpoint | Human rejects entirely |
| Build | Test | CodeBundle produced + validation passed |
| Build | Build (self-retry) | Validation failed (syntax/import/schema), max 1 self-retry |
| Test | Learner | all tests passed |
| Test | Builder | code-level failure AND build_iteration < MAX_BUILD_ITERATIONS |
| Test | Architecture | spec-level failure AND build_iteration < MAX_BUILD_ITERATIONS |
| Test | Learner | build_iteration >= MAX_BUILD_ITERATIONS (partial success flag) |
| Learner | END | BuildOutcome stored |

## Requirements Checkpoint (Human Gate 1)

Present `RequirementsDoc` in readable format:
- **Domain** and high-level summary
- **Inputs/Outputs** — each with name, format, description, example
- **Process Steps** — numbered, with rules and dependencies
- **Edge Cases** — with expected handling behavior
- **Quality Criteria** — with validation methods
- **Constraints** — budget, time, technical
- **Assumptions** — fields the Elicitor couldn't fully resolve (scored < 0.7 after max rounds), flagged explicitly

Human actions:
- **Approve** → set `requirements_approved = true`, route to Architecture
- **Correct** → merge human edits into RequirementsDoc, set approved, route to Architecture
- **Reject** → route back to Elicitation with human's feedback attached as additional context

## Spec Checkpoint (Human Gate 2)

Present `AgentSpec` + `CritiqueReport`:
- **Agent roles** — id, role, goal, tools assigned
- **Flow diagram** — execution pattern with edges and conditions
- **Tool selections** — which tools, why, format chain compatibility
- **Critique findings** — severity-colored (critical=red, warning=yellow, suggestion=blue)
- **Remaining issues** — warnings/suggestions that didn't block progression
- **Iteration count** — how many Architect-Critic loops ran

Human actions:
- **Approve** → set `spec_approved = true`, route to Build
- **Request changes** → attach feedback to state, route to Architecture (increments spec_iteration)
- **Reject** → route back to Requirements Checkpoint for re-evaluation

## Stage References

| Stage | Reference | Details |
|-------|-----------|---------|
| Elicitation | `references/elicitation.md` | Domain extraction, gap analysis, Q&A loop |
| Architecture | `references/architecture.md` | RAG queries, spec generation, tool matching |
| Critique | `references/critique.md` | Adversarial spec review, 6 attack vectors |
| Build | `references/build.md` | Template-driven code compilation |
| Test | `references/test.md` | Docker execution, failure tracing |
| Learn | `references/learn.md` | Chroma storage, pattern extraction |

## Design Rationale

**Cross-model adversarial review:** Architect (Claude) and Critic (GPT-4o) deliberately use different model families. Same-model review shares blind spots — the Critic must be a different "thinker" to catch what the Architect missed. This is why model routing is not arbitrary.

**Template-driven code generation:** Builder compiles from templates, not free-form LLM code generation. Free-form produces creative but unreliable code with subtle bugs. Templates are deterministic — same spec structure always produces same code structure. The LLM's job is selecting and configuring templates, not inventing code.

**Two-level failure routing:** Tester distinguishes code-level failures (Builder can fix without redesign) from spec-level failures (the Architect made a fundamentally wrong design decision). Without this, every test failure would trigger a full spec redesign, wasting iterations on bugs that need a one-line code fix.

**Human checkpoints as trust mechanism:** The two gates exist because the system handles irreversible decisions (architecture, tool selection). Humans validate the "what" (requirements) and the "how" (spec) before Frankenstein executes autonomously. Removing checkpoints defeats the product's trust model.

**Future configurability note:** This workflow is fixed for hackathon scope. The natural customization surface: model routing per agent, MAX_SPEC_ITERATIONS / MAX_BUILD_ITERATIONS / MAX_ELICITOR_ROUNDS, DOCKER_TIMEOUT, tool library path, Chroma collection names, generated code output directory.
