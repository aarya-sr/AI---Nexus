# Story 1.3: Elicitor Agent — Requirements Extraction

## Status: review

## Story

As a **user**,
I want the system to ask me smart, targeted questions about my workflow so it understands what I need,
So that the generated agents are built on solid, complete requirements — not guesswork.

## Acceptance Criteria (ACs)

### AC1: Domain Context Query (FR65)

Given a user submits a natural language prompt via WebSocket (`control.user_input` message on `/ws/chat/{session_id}`),
When the Elicitor agent begins processing,
Then it calls `chroma_service.query_domain_insights(domain)` to retrieve any stored domain-specific question templates and context,
And if the collection is empty or no relevant matches exist, the query returns an empty list and the agent proceeds without error,
And the returned insights (if any) are appended to the system prompt for the gap analysis LLM call.

### AC2: 5-Category Gap Analysis (FR2)

Given a raw prompt string is available in `state["raw_prompt"]`,
When the Elicitor runs gap analysis via LLM call (model: `openai/gpt-4o-mini`, `json_mode=True`),
Then the LLM evaluates the prompt against exactly 5 categories: **Input/Output**, **Process**, **Data**, **Edge Cases**, **Quality Bar**,
And returns a confidence score between 0.0 and 1.0 for each category,
And returns the list of specific fields that are missing or unclear within each category.

### AC3: Targeted Question Generation — Gap Categories Only (FR3, FR9)

Given the gap analysis result with per-category confidence scores,
When one or more categories score below 0.7,
Then the Elicitor generates questions **only** for the gap categories (categories >= 0.7 are skipped),
And for prompts where the overall quality is low (all categories below 0.5, or the prompt is 10 words or fewer), at least 2 questions are generated per gap category,
And questions are ordered by category priority: Input/Output first, then Process, then Data, then Edge Cases, then Quality Bar.

### AC4: WebSocket Delivery of Questions (FR4, UX-DR8)

Given questions are generated for one or more gap categories,
When the Elicitor sends questions to the frontend,
Then the backend emits a `chat.question_group` WebSocket message on `/ws/chat/{session_id}` conforming to:
```json
{
  "type": "chat.question_group",
  "payload": {
    "categories": [
      {
        "name": "Input/Output",
        "confidence": 0.4,
        "questions": ["What format is the input data?", "What should the output look like?"]
      }
    ],
    "round": 1,
    "max_rounds": 3
  },
  "timestamp": "<ISO 8601 UTC>",
  "session_id": "<uuid>"
}
```
And `state["elicitor_questions"]` is updated to include the sent questions with their category metadata,
And the pipeline execution pauses awaiting a `control.user_input` message from the frontend (LangGraph interrupt/checkpoint mechanism).

### AC5: QuestionGroup Frontend Rendering (UX-DR8)

Given a `chat.question_group` message arrives at the frontend,
When the `QuestionGroup` component renders,
Then category labels render at 11px uppercase in amber (#f59e0b),
And each question renders with a 2px left border,
And the containing card uses surface-elevated background (#262626), 12px border-radius, 20px padding,
And the component fades up 12px in 250ms (same as ChatMessage entry animation).

### AC6: Answer Processing and Re-scoring (FR4, FR5)

Given the user submits answers via `control.user_input` message,
When the Elicitor processes the answers,
Then it appends the answers to `state["human_answers"]` as a dict `{"round": N, "answers": <text>, "timestamp": <ISO UTC>}`,
And calls the LLM (model: `openai/gpt-4o-mini`, `json_mode=True`) to extract structured field values from the free-text answers,
And updates the in-progress `RequirementsDoc` with extracted values,
And re-runs gap analysis to produce updated confidence scores for all 5 categories.

### AC7: Follow-up Loop (FR5)

Given re-scoring is complete and at least one category still scores below 0.7,
When the current round count is less than `MAX_ELICITOR_ROUNDS` (3),
Then the Elicitor generates follow-up questions targeting only the still-incomplete categories,
And sends another `chat.question_group` message with `"round": N+1`,
And the loop repeats from AC4.

### AC8: Max Rounds — Assumption Flagging (FR5)

Given 3 rounds of Q&A have completed and gaps remain (any category still below 0.7),
When the Elicitor checks the round counter against `MAX_ELICITOR_ROUNDS`,
Then it does NOT generate more questions,
And for each remaining low-confidence field, it generates a best-guess assumption string (LLM-assisted),
And appends each assumption to `requirements.assumptions` in the `RequirementsDoc`,
And proceeds to compilation (AC9).

### AC9: RequirementsDoc Compilation (FR6)

Given all categories score >= 0.7 OR `MAX_ELICITOR_ROUNDS` (3) has been reached,
When the Elicitor compiles the final output,
Then it calls the LLM (model: `openai/gpt-4o-mini`, `json_mode=True`) to compile all extracted information into a complete `RequirementsDoc`,
And the resulting object conforms to the `RequirementsDoc` Pydantic model with all required fields populated,
And `state["requirements"]` is set to the compiled `RequirementsDoc`,
And `state["requirements_approved"]` is set to `False` (approval handled by human checkpoint in Story 1.4).

### AC10: LLM Routing (FR55, FR57)

Given any LLM call is made within the Elicitor,
When routed through `llm_service.call()`,
Then the model parameter is always `openai/gpt-4o-mini`,
And `json_mode=True` is passed for all structured output calls,
And on LLM failure, the service retries up to 3 times with exponential backoff before raising,
And on final retry failure, a structured `error.llm_failure` message is sent via status WebSocket.

### AC11: Pipeline Graph Registration

Given the Elicitor agent function `elicitor_agent` is implemented in `backend/app/agents/elicitor.py`,
When `backend/app/pipeline/graph.py` is updated,
Then the graph registers `elicitor_agent` as the `"elicitor"` node,
And `graph.add_edge("elicitor", "human_review_requirements")` is present,
And the graph compiles without error.

---

## Technical Implementation Notes

### Architecture

**Files this story creates or modifies:**

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/agents/elicitor.py` | Create | Main agent logic — gap analysis, question generation, answer processing, compilation |
| `backend/app/models/requirements.py` | Create (may exist from 1.1) | Pydantic models: `RequirementsDoc`, `DataSpec`, `ProcessStep`, `EdgeCase`, `QualityCriterion`, `CategoryAssessment`, `GapAnalysisResult` |
| `backend/app/pipeline/graph.py` | Modify | Add elicitor node and edge to `human_review_requirements` |

**Files this story depends on (built in Story 1.1):**

| File | Interface used |
|------|---------------|
| `backend/app/services/llm_service.py` | `llm_service.call(model, messages, json_mode)` singleton |
| `backend/app/services/chroma_service.py` | `chroma_service.query_domain_insights(domain)` |
| `backend/app/models/state.py` | `FrankensteinState` TypedDict |
| `backend/app/models/messages.py` | `QuestionGroupMessage` Pydantic model |

**Dependency direction:** `models` <- `services` <- `agents` <- `pipeline`. The elicitor imports from models and services only. No agent-to-agent imports.

---

### Elicitor Agent Design

#### Subgraph Loop

The Elicitor is implemented as a single LangGraph node function (`elicitor_agent`) that contains its own internal async loop. It is NOT a LangGraph subgraph — it is a self-contained async function that loops internally and uses LangGraph's interrupt mechanism to pause at each question-answer round.

```
elicitor_agent() called by LangGraph
    │
    ├─ Step 1: Query domain_insights (Chroma)
    │
    ├─ Step 2: Analyze prompt → GapAnalysisResult (LLM call #1)
    │
    ├─ Loop (max MAX_ELICITOR_ROUNDS = 3 iterations):
    │   ├─ identify_gaps(gap_analysis_result) → gap categories
    │   ├─ generate_questions(gaps, domain_insights) → QuestionGroup (LLM call #2)
    │   ├─ send chat.question_group via WebSocket
    │   ├─ interrupt() — wait for control.user_input
    │   ├─ process_answers(user_input) → extracted fields (LLM call #3)
    │   ├─ update_requirements_doc(extracted_fields)
    │   └─ re_score_categories() → GapAnalysisResult (LLM call #4, same as #1)
    │       └─ if all >= 0.7: break
    │       └─ if round == MAX_ELICITOR_ROUNDS: flag_assumptions(), break
    │
    └─ Step 3: Compile RequirementsDoc (LLM call #5)
         └─ write state["requirements"], state["requirements_approved"] = False
         └─ return updated FrankensteinState
```

#### Gap Analysis — 5 Categories and Their Required Fields

Each category has a defined set of required fields. The LLM assigns a confidence score per category based on how completely the prompt (and accumulated answers) address all required fields in that category.

**Category 1: Input/Output** (priority 1 — asked first)
- Required fields: `input_data_type`, `input_format`, `input_source`, `output_data_type`, `output_format`, `output_destination`
- Low confidence triggers questions like: "What is the format of the data you'll be feeding in?", "Where does the output need to go?"

**Category 2: Process** (priority 2)
- Required fields: `main_task_description`, `process_steps_count`, `decision_points`, `transformation_logic`, `sequencing_rules`
- Low confidence triggers questions like: "Walk me through the steps the agent should take, in order.", "Are there any branching decisions the agent needs to make?"

**Category 3: Data** (priority 3)
- Required fields: `data_volume_estimate`, `data_frequency`, `data_sensitivity`, `external_data_sources`, `data_schema_known`
- Low confidence triggers questions like: "How often will this agent run — on-demand, scheduled, or continuously?", "Is the data structure fixed or does it vary?"

**Category 4: Edge Cases** (priority 4)
- Required fields: `known_failure_modes`, `missing_data_handling`, `invalid_input_handling`, `timeout_behavior`, `partial_success_handling`
- Low confidence triggers questions like: "What should the agent do if a required input is missing?", "What's the acceptable behavior when the process partially fails?"

**Category 5: Quality Bar** (priority 5 — asked last)
- Required fields: `accuracy_requirement`, `latency_requirement`, `output_validation_method`, `success_criteria`, `acceptable_error_rate`
- Low confidence triggers questions like: "How will you know if the agent's output is correct?", "Are there any speed or latency requirements?"

**Confidence scoring rules:**
- `1.0`: All required fields in the category are clearly addressed with specific, usable values
- `0.7-0.99`: Most fields addressed, minor ambiguities that can be inferred reasonably
- `0.4-0.69`: Some fields addressed but significant gaps remain
- `0.0-0.39`: Category barely touched — raw prompt says almost nothing about this area
- Threshold for proceeding without questions: `>= 0.7`

#### Low-Quality Prompt Detection

A prompt is classified as "low quality" if:
- It is 10 words or fewer, OR
- All 5 category confidence scores are below 0.5

When low quality is detected, the Elicitor generates at least 2 questions per gap category (instead of the usual minimum of 1). This ensures the user is guided toward sufficient input before meaningful Q&A ends.

#### Question Prioritization

When multiple gap categories exist, questions are batched into a single `chat.question_group` message. Within the message, category blocks appear in this fixed order regardless of confidence score:
1. Input/Output
2. Process
3. Data
4. Edge Cases
5. Quality Bar

This ordering means the most architecturally critical information (what goes in, what comes out) is always asked first.

---

### Data Models

All models live in `backend/app/models/requirements.py`. Use absolute imports: `from app.models.requirements import RequirementsDoc`.

```python
from __future__ import annotations
from pydantic import BaseModel
from typing import Literal


class DataSpec(BaseModel):
    name: str                  # e.g. "bank_statement"
    format: str                # e.g. "pdf", "csv", "json"
    description: str           # human-readable description of what this data is
    example: str               # concrete example value or filename


class ProcessStep(BaseModel):
    step_number: int
    description: str           # what happens in this step
    rules: list[str]           # business rules that govern this step
    depends_on: list[int]      # step_numbers this step depends on (empty = start node)


class EdgeCase(BaseModel):
    description: str           # what the edge case is
    expected_handling: str     # how the agent should respond to it


class QualityCriterion(BaseModel):
    criterion: str             # e.g. "output.risk_score must be between 0 and 1"
    validation_method: str     # e.g. "schema validation", "manual spot check"


class RequirementsDoc(BaseModel):
    domain: str                        # e.g. "loan underwriting", "supplier scoring"
    inputs: list[DataSpec]             # what the agent receives
    outputs: list[DataSpec]            # what the agent produces
    process_steps: list[ProcessStep]   # ordered workflow steps
    edge_cases: list[EdgeCase]         # known failure modes + handling
    quality_criteria: list[QualityCriterion]  # success conditions
    constraints: list[str]             # budget, time, technical constraints
    assumptions: list[str] = []        # gaps flagged after MAX_ELICITOR_ROUNDS


# Supporting models for internal Elicitor use only
# (not written to pipeline state — used during agent execution)

class CategoryAssessment(BaseModel):
    name: Literal["Input/Output", "Process", "Data", "Edge Cases", "Quality Bar"]
    confidence: float          # 0.0 to 1.0
    addressed_fields: list[str]
    missing_fields: list[str]
    notes: str                 # brief LLM rationale for the score


class GapAnalysisResult(BaseModel):
    categories: list[CategoryAssessment]
    overall_quality: Literal["high", "medium", "low"]
    # high: all >= 0.7 | medium: some >= 0.7 | low: all < 0.5 or prompt <= 10 words

    def gaps(self) -> list[CategoryAssessment]:
        """Return only categories below 0.7 threshold, in priority order."""
        priority_order = ["Input/Output", "Process", "Data", "Edge Cases", "Quality Bar"]
        below_threshold = [c for c in self.categories if c.confidence < 0.7]
        return sorted(below_threshold, key=lambda c: priority_order.index(c.name))

    def all_complete(self) -> bool:
        return all(c.confidence >= 0.7 for c in self.categories)


class QuestionCategory(BaseModel):
    name: str
    confidence: float
    questions: list[str]
```

---

### LLM Prompt Design

All LLM calls go through `llm_service.call(model="openai/gpt-4o-mini", messages=[...], json_mode=True)`. The service handles retry and structured output parsing. The Elicitor is responsible for constructing the message lists and parsing the returned dicts into Pydantic models.

#### LLM Call #1 — Gap Analysis (initial prompt + re-scoring after each answer round)

**System prompt:**
```
You are an expert requirements analyst for AI agent systems. Your job is to evaluate how
completely a user's natural language description addresses 5 key categories needed to build
a working AI agent pipeline.

Categories and their required fields:

1. Input/Output: input_data_type, input_format, input_source, output_data_type,
   output_format, output_destination
2. Process: main_task_description, process_steps_count, decision_points,
   transformation_logic, sequencing_rules
3. Data: data_volume_estimate, data_frequency, data_sensitivity,
   external_data_sources, data_schema_known
4. Edge Cases: known_failure_modes, missing_data_handling, invalid_input_handling,
   timeout_behavior, partial_success_handling
5. Quality Bar: accuracy_requirement, latency_requirement, output_validation_method,
   success_criteria, acceptable_error_rate

Scoring rules:
- 1.0: All required fields clearly addressed with specific, usable values
- 0.7-0.99: Most fields addressed, minor ambiguities inferable from context
- 0.4-0.69: Some fields addressed but significant gaps remain
- 0.0-0.39: Category barely touched

Domain insights (from past builds, may be empty): {domain_insights}

Respond ONLY with valid JSON matching this exact schema:
{
  "categories": [
    {
      "name": "<category name>",
      "confidence": <float 0.0-1.0>,
      "addressed_fields": ["<field>", ...],
      "missing_fields": ["<field>", ...],
      "notes": "<1-2 sentence rationale>"
    }
  ],
  "overall_quality": "<high|medium|low>"
}
```

**User message (initial):**
```
Analyze this agent description for completeness:

"{raw_prompt}"
```

**User message (re-scoring after answers):**
```
Re-analyze the updated description for completeness.

Original prompt: "{raw_prompt}"

Additional information provided:
Round 1: {round_1_answers}
Round 2: {round_2_answers}  (if applicable)

Assign updated confidence scores based on ALL information above.
```

---

#### LLM Call #2 — Question Generation

**System prompt:**
```
You are an expert requirements analyst conducting a structured interview to gather
information needed to build an AI agent pipeline. Your questions must be specific,
targeted, and immediately actionable. Do not ask general or open-ended questions.

You are building requirements in these gap categories: {gap_category_names}
Minimum questions per category: {min_questions_per_category}
This is round {current_round} of {max_rounds}.

Rules:
- Ask only about the missing fields identified in the gap analysis
- Questions must be specific enough that the user's answer directly fills a field
- Do not repeat questions from previous rounds
- Use plain business language — no technical jargon
- For round 2+, acknowledge what was already provided and ask only about remaining gaps

Previous questions asked (do not repeat): {previous_questions}

Respond ONLY with valid JSON:
{
  "categories": [
    {
      "name": "<category name>",
      "confidence": <current confidence float>,
      "questions": ["<question 1>", "<question 2>", ...]
    }
  ]
}
Only include categories that have gaps (confidence < 0.7).
```

**User message:**
```
Gap analysis results for the following description:

Prompt: "{raw_prompt}"
Accumulated answers: {accumulated_answers_text}

Gap categories requiring questions:
{gap_categories_json}

Generate targeted questions for each gap category.
```

---

#### LLM Call #3 — Answer Extraction (field value extraction from free-text answers)

**System prompt:**
```
You are extracting structured requirement information from a user's conversational answer.
The user was answering these specific questions about building an AI agent:

Questions asked:
{questions_asked}

Extract the values for these fields from the user's answer:
{target_fields}

If the user did not address a field, use null for that field's value.
Do not infer or hallucinate — only extract explicitly stated information.

Respond ONLY with valid JSON:
{
  "extracted_fields": {
    "<field_name>": "<extracted value or null>",
    ...
  },
  "coverage_notes": "<brief note on what was and wasn't answered>"
}
```

**User message:**
```
User's answer: "{user_answer_text}"
```

---

#### LLM Call #4 — Assumption Generation (called only when MAX_ELICITOR_ROUNDS reached with gaps)

**System prompt:**
```
You are generating safe, conservative assumptions to fill in missing requirements
for an AI agent pipeline. These assumptions will be flagged explicitly in the
requirements document so the human can review them.

Make assumptions that:
- Are the simplest reasonable interpretation of the domain
- Err toward less risky defaults (e.g., assume human review is needed when uncertain)
- Are stated clearly so the user can confirm or correct them later

Respond ONLY with valid JSON:
{
  "assumptions": [
    "<Assumption 1: e.g., 'Assuming input data arrives as a single file per run, not streaming'>",
    ...
  ]
}
```

**User message:**
```
Domain: {domain}
Prompt so far: "{raw_prompt}"
Accumulated answers: {accumulated_answers_text}

Missing fields that need assumptions:
{remaining_missing_fields}

Generate one assumption per missing field.
```

---

#### LLM Call #5 — Final RequirementsDoc Compilation

**System prompt:**
```
You are compiling a structured requirements document for an AI agent pipeline.
You will receive all information gathered from the user across multiple rounds of Q&A.
Your job is to organize this into a clean, complete RequirementsDoc.

Rules:
- Only include information that was explicitly provided or is a stated assumption
- process_steps must be ordered logically with correct depends_on references
- edge_cases must be specific and actionable (not generic)
- quality_criteria must be measurable
- constraints are hard limits (budget, time, technical)
- assumptions are gaps that could not be resolved after {max_rounds} Q&A rounds

Respond ONLY with valid JSON matching this exact schema:
{
  "domain": "<domain string>",
  "inputs": [
    {"name": "<str>", "format": "<str>", "description": "<str>", "example": "<str>"}
  ],
  "outputs": [
    {"name": "<str>", "format": "<str>", "description": "<str>", "example": "<str>"}
  ],
  "process_steps": [
    {
      "step_number": <int>,
      "description": "<str>",
      "rules": ["<rule>", ...],
      "depends_on": [<step_number>, ...]
    }
  ],
  "edge_cases": [
    {"description": "<str>", "expected_handling": "<str>"}
  ],
  "quality_criteria": [
    {"criterion": "<str>", "validation_method": "<str>"}
  ],
  "constraints": ["<str>", ...],
  "assumptions": ["<str>", ...]
}
```

**User message:**
```
Compile a RequirementsDoc from ALL of the following gathered information:

Original prompt: "{raw_prompt}"

Round-by-round Q&A:
{formatted_qa_history}

Assumptions generated for missing fields:
{assumptions_list}

Domain insights applied:
{domain_insights_summary}
```

---

### Pipeline Integration

#### State Fields Written by This Story

```python
# In FrankensteinState (backend/app/models/state.py)
# These fields must exist before elicitor.py is implemented:

raw_prompt: str                    # Written by main.py WebSocket handler before pipeline.invoke()
elicitor_questions: list[dict]     # Written by elicitor_agent — list of QuestionCategory dicts
human_answers: list[dict]          # Written by elicitor_agent — [{round: int, answers: str, timestamp: str}]
requirements: RequirementsDoc      # Written by elicitor_agent on completion
requirements_approved: bool        # Written by elicitor_agent as False; set to True by Story 1.4
```

#### Graph Registration (backend/app/pipeline/graph.py)

```python
from langgraph.graph import StateGraph, END
from app.models.state import FrankensteinState
from app.agents.elicitor import elicitor_agent
from app.pipeline.checkpoints import human_checkpoint_requirements  # Story 1.4

graph = StateGraph(FrankensteinState)

graph.add_node("elicitor", elicitor_agent)
graph.add_node("human_review_requirements", human_checkpoint_requirements)

graph.set_entry_point("elicitor")
graph.add_edge("elicitor", "human_review_requirements")

# Story 2.x will add: architect, critic, etc.

compiled_graph = graph.compile()
```

#### How main.py Invokes the Pipeline

The `elicitor_agent` node is called by LangGraph automatically when `compiled_graph.invoke(initial_state)` or `compiled_graph.astream(initial_state)` is called. The WebSocket handler in `main.py` is responsible for:

1. Creating the initial state with `raw_prompt` populated
2. Invoking the graph (async stream)
3. Forwarding any `chat.question_group` messages emitted by elicitor to the chat WebSocket
4. Receiving `control.user_input` from the chat WebSocket and resuming graph execution with the user's answers

The interrupt/resume mechanism uses LangGraph's built-in `interrupt()` call inside the agent, paired with `compiled_graph.invoke(Command(resume=user_answer), config=config)` from main.py.

---

### WebSocket Integration

#### Outbound: Questions to Frontend

The Elicitor emits questions by calling a helper that sends on the chat WebSocket. Since the Elicitor is a graph node (not a FastAPI route), it accesses the WebSocket via the session's connection registry stored in `session_service`.

```python
# Inside elicitor_agent, before interrupt:
await send_ws_message(
    session_id=state["session_id"],
    message=QuestionGroupMessage(
        type="chat.question_group",
        payload=QuestionGroupPayload(
            categories=[
                QuestionCategory(name=c.name, confidence=c.confidence, questions=questions_for_category)
                for c in gaps
            ],
            round=current_round,
            max_rounds=MAX_ELICITOR_ROUNDS,
        ),
        timestamp=datetime.utcnow().isoformat() + "Z",
        session_id=state["session_id"],
    )
)
```

#### Inbound: User Answers from Frontend

The frontend sends user answers as:
```json
{
  "type": "control.user_input",
  "payload": {
    "text": "<user's free-text answer to all questions in this round>"
  },
  "timestamp": "...",
  "session_id": "..."
}
```

`main.py` receives this on `/ws/chat/{session_id}`, pulls the text, and resumes the LangGraph execution with it. The Elicitor receives the resumed value as the return value of `interrupt()`.

#### Status Updates via Status WebSocket

The Elicitor sends stage update messages on the status WebSocket at key transitions:

| Moment | Message type | Payload |
|--------|-------------|---------|
| Elicitor node starts | `status.stage_update` | `{stage: "elicitor", status: "active", description: "Understanding your needs..."}` |
| Each Q&A round starts | `status.progress` | `{stage: "elicitor", progress: round/max_rounds, message: "Gathering requirements (round N of 3)..."}` |
| Compilation starts | `status.progress` | `{stage: "elicitor", progress: 0.9, message: "Compiling your requirements..."}` |
| Node completes | `status.stage_update` | `{stage: "elicitor", status: "complete", description: "Requirements ready for review"}` |

---

### Key Technical Decisions

#### Decision 1: Internal loop vs. LangGraph subgraph

The Elicitor uses an **internal Python loop with LangGraph interrupt** rather than a dedicated LangGraph subgraph. Rationale: a subgraph would require defining sub-nodes for analyze/identify/generate/receive/update/check, adding boilerplate without benefit. The interrupt/resume mechanism handles the human-in-the-loop pause cleanly within a single node function. If the Elicitor's internal complexity grows significantly (post-MVP), it can be refactored into a subgraph without changing its external interface.

#### Decision 2: Free-text answers, structured extraction

The Elicitor accepts **free-text conversational answers** from the user and uses a dedicated LLM call (LLM Call #3) to extract structured field values. This is deliberate — forcing users to fill structured fields breaks the conversational UX contract. The extraction LLM is explicitly instructed not to hallucinate, using `null` for fields not addressed.

#### Decision 3: Re-scoring uses the same prompt as initial analysis

After each answer round, the Elicitor re-runs gap analysis (LLM Call #1 prompt) against the **full accumulated context** (original prompt + all rounds of answers). This is simpler and more accurate than delta-scoring — the LLM sees everything and produces fresh scores. The cost is one extra LLM call per loop iteration, acceptable given `gpt-4o-mini` speed.

#### Decision 4: MAX_ELICITOR_ROUNDS = 3 is a config constant

`MAX_ELICITOR_ROUNDS` is defined in `backend/app/config.py` via `pydantic-settings`, loaded from the `.env` file. It is NOT hardcoded in `elicitor.py`. This allows adjustment without code changes.

```python
# backend/app/config.py
class Settings(BaseSettings):
    MAX_ELICITOR_ROUNDS: int = 3
    ELICITOR_CONFIDENCE_THRESHOLD: float = 0.7
    # ...
```

#### Decision 5: Chroma query is non-blocking on empty

`chroma_service.query_domain_insights()` returns an empty list `[]` when the collection has no relevant matches. The Elicitor handles this gracefully — domain insights are passed as an optional context enhancement to LLM Call #1 and #2. When empty, the system prompt uses a placeholder: `"No domain insights available for this domain."` The agent functions fully from first principles without past data.

#### Decision 6: `session_id` in pipeline state

`FrankensteinState` must include `session_id: str` so agents can reference it when emitting WebSocket messages. This field is set by `main.py` before graph invocation and is read-only for all agents.

---

## Dev Notes

### Implementation Order

Implement in this order to minimize blocked work:

1. `backend/app/models/requirements.py` — all Pydantic models first (nothing else can proceed without these)
2. `backend/app/config.py` — add `MAX_ELICITOR_ROUNDS` and `ELICITOR_CONFIDENCE_THRESHOLD` if not already present
3. `backend/app/agents/elicitor.py` — implement `elicitor_agent` function (can stub LLM calls initially)
4. `backend/app/pipeline/graph.py` — register the elicitor node (even with a stub, this validates the graph compiles)
5. Write tests in `backend/tests/test_elicitor.py`

### Testing Strategy

**Unit tests (`backend/tests/test_elicitor.py`):**

- `test_gap_analysis_high_quality_prompt`: Given a detailed prompt covering all 5 categories, all scores should be >= 0.7
- `test_gap_analysis_empty_prompt`: Given an empty or very short prompt, all scores should be < 0.5, `overall_quality == "low"`
- `test_low_quality_prompt_minimum_two_questions`: Given a low-quality prompt, each gap category must have >= 2 questions
- `test_question_priority_order`: Given gaps in Input/Output and Edge Cases, Input/Output questions must appear first
- `test_max_rounds_assumption_flagging`: Given 3 rounds of Q&A with persistent gaps, `requirements.assumptions` must be non-empty
- `test_requirements_doc_compilation_fields`: After compilation, all required fields on `RequirementsDoc` are populated (not None, not empty lists for prompts that provided data)
- `test_chroma_empty_returns_gracefully`: `query_domain_insights()` returning `[]` does not raise
- `test_llm_routing_model_name`: Every LLM call inside elicitor uses `openai/gpt-4o-mini` — assert on mock

**Mock strategy:** Mock `llm_service.call()` to return canned `GapAnalysisResult` and `RequirementsDoc` JSON. Mock `chroma_service.query_domain_insights()` for both empty and populated cases.

### Common Failure Modes to Guard Against

1. **LLM returns JSON with extra wrapper keys** — parse defensively; validate against Pydantic model after `json.loads()`, not before
2. **User answer spans multiple sentences addressing multiple categories** — LLM Call #3 extraction handles this; do NOT try to split by category in Python
3. **`depends_on` in `ProcessStep` references a non-existent step_number** — add a post-compilation validation pass that checks all `depends_on` values exist as `step_number` values in the list
4. **Round counter not incrementing** — maintain `current_round` as a local variable inside the loop, not in pipeline state (state is only updated at loop exit)
5. **WebSocket send fails mid-loop** — wrap each `send_ws_message` call in a try/except; log the failure but do not abort the elicitor loop; the pipeline should not crash because a WS send failed

### Environment Variables Required

```bash
# .env (must exist before running)
OPENROUTER_API_KEY=sk-or-...
MAX_ELICITOR_ROUNDS=3
ELICITOR_CONFIDENCE_THRESHOLD=0.7
```

### Absolute Import Reminder

```python
# CORRECT
from app.models.requirements import RequirementsDoc, DataSpec, GapAnalysisResult
from app.models.state import FrankensteinState
from app.models.messages import QuestionGroupMessage
from app.services.llm_service import llm_service
from app.services.chroma_service import chroma_service
from app.config import settings

# WRONG — never use relative imports
from ..models.requirements import RequirementsDoc
from models.requirements import RequirementsDoc
```

### No Print Statements

Use Python `logging` exclusively:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Elicitor starting for session %s", session_id)
logger.debug("Gap analysis result: %s", gap_result.model_dump())
logger.warning("Round %d complete with remaining gaps: %s", current_round, [c.name for c in gaps])
logger.error("LLM call failed in elicitor: %s", str(exc))
```

### Story Dependencies

This story requires Story 1.1 to be complete (or at minimum have stub interfaces) for:
- `llm_service` singleton with `call(model, messages, json_mode)` signature
- `chroma_service` singleton with `query_domain_insights(domain)` returning `list[dict]`
- `FrankensteinState` TypedDict with the fields listed under "State Fields Written by This Story"
- `QuestionGroupMessage` Pydantic model in `backend/app/models/messages.py`

The frontend `QuestionGroup.tsx` component (AC5 rendering) is defined in Story 1.2. This story only needs the backend to emit the correct `chat.question_group` message — the component is a separate deliverable.

Human checkpoint (`human_review_requirements` node) is implemented in Story 1.4. For this story, the graph edge to that node just needs to exist; the checkpoint node itself can be a stub that immediately returns `state`.

---

## Dev Agent Record

### Implementation Plan

1. Added `CategoryAssessment`, `GapAnalysisResult`, `QuestionCategory` models to `requirements.py`
2. Added `session_id` to `FrankensteinState`
3. Implemented `elicitor_agent` as single LangGraph node with internal Q&A loop using `interrupt()` for human-in-the-loop pauses
4. Created pipeline `graph.py` with elicitor node + stub checkpoint node + edge
5. Wrote 22 unit tests covering all ACs

### Debug Log

- `langgraph` not in requirements.txt — installed via pip
- Used `interrupt()` from `langgraph.types` for pause/resume pattern instead of direct WebSocket access — cleaner architecture, agents don't need WS dependencies
- AC5 (frontend QuestionGroup rendering) deferred to Story 1.2 — confirmed in story notes as separate deliverable

### Completion Notes

- All 11 ACs addressed (AC5 is frontend-only, deferred to Story 1.2)
- 22 tests pass, 53 total tests pass (zero regressions)
- Elicitor uses LangGraph `interrupt()` for human-in-the-loop — `main.py` (Story 1.1) handles WS transport
- Gap analysis enforces 5-category priority ordering
- Low-quality prompt detection triggers min 2 questions per gap
- Max rounds (3) triggers assumption generation for remaining gaps
- All LLM calls routed through `agent_name="elicitor"` with `json_mode=True`

## File List

| File | Action |
|------|--------|
| `backend/app/models/requirements.py` | Modified — added CategoryAssessment, GapAnalysisResult, QuestionCategory |
| `backend/app/models/state.py` | Modified — added session_id field |
| `backend/app/models/__init__.py` | Modified — exported new models |
| `backend/app/agents/__init__.py` | Created — package init |
| `backend/app/agents/elicitor.py` | Created — main agent implementation |
| `backend/app/pipeline/__init__.py` | Created — package init |
| `backend/app/pipeline/graph.py` | Created — StateGraph with elicitor + stub checkpoint |
| `backend/tests/test_elicitor.py` | Created — 22 unit tests |

## Change Log

- 2026-05-14: Implemented Story 1.3 — Elicitor agent with 5-category gap analysis, Q&A loop (max 3 rounds), assumption flagging, RequirementsDoc compilation, pipeline graph registration. 22 tests added.
