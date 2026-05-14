# Learn Stage

**Agent:** Learner | **Model:** gpt-4o-mini | **Input:** final FrankensteinState | **Output:** BuildOutcome → Chroma

The Learner is the pipeline's memory writer. After every build (successful or not), it extracts what happened, why, and what patterns emerged, then stores structured records in Chroma for future RAG retrieval. Every build makes the next build smarter.

## Data Models

```python
class BuildOutcome(BaseModel):
    # Identity
    requirements_hash: str            # hash for similarity matching
    requirements_summary: str         # embedded for RAG retrieval
    domain: str                       # "loan_underwriting"

    # What was built
    spec_snapshot: AgentSpec           # the final validated spec
    framework_used: str               # "crewai" or "langgraph"
    tools_used: list[str]             # tool IDs from library

    # How it went
    test_results: TestReport           # final test report
    iterations_needed: int             # total architect-critic + build-test loops
    total_time_seconds: float          # wall clock time for full pipeline

    # Patterns extracted
    success_patterns: list[str]        # patterns that worked well
    failure_patterns: list[str]        # what went wrong and was fixed
    anti_patterns: list[str]           # patterns that caused failures
    lessons_learned: list[str]         # free-form insights

    # Status
    outcome: Literal["success", "partial_success", "failure"]
    partial_success_details: str | None  # what worked, what didn't
```

## Internal Process

```
Read full pipeline state
       ↓
Compute build metadata (hash, timing, iteration counts)
       ↓
Extract patterns (success, failure, anti)
       ↓
Generate requirements summary for embedding
       ↓
Assemble BuildOutcome
       ↓
Write to Chroma collections:
  → spec_patterns (successful specs)
  → anti_patterns (failure patterns)
  → domain_insights (domain learnings)
       ↓
Output BuildOutcome as final pipeline record
```

## Step 1: Compute Build Metadata

```python
# Requirements hash — for deduplication and similarity matching
requirements_hash = hashlib.sha256(
    json.dumps(state["requirements"].dict(), sort_keys=True).encode()
).hexdigest()[:16]

# Iteration count — total loops across both feedback cycles
iterations_needed = state["spec_iteration"] + state["build_iteration"]

# Outcome classification
if state["test_results"].all_passed:
    outcome = "success"
elif state["test_results"].passed > 0:
    outcome = "partial_success"
else:
    outcome = "failure"
```

## Step 2: Extract Patterns

The Learner's most important job. It reads the full state history and extracts generalizable patterns.

### Success Patterns

What worked well — things the Architect should repeat in future similar builds:

- **Tool combinations** that worked together smoothly (format chains that didn't break)
- **Agent groupings** that produced clean handoffs
- **Flow patterns** that matched the domain well
- **Memory strategies** that worked for the data volume

**How to identify:** Look at what DIDN'T cause failures. Look at what the Critic praised or didn't flag. Look at tool chains that passed all format compatibility checks.

**Example success patterns (PS-08):**
```json
[
  "pdf_parser_pymupdf → json_transformer chain handles standard bank statements cleanly",
  "Grouping extraction + parsing in one agent reduces data serialization overhead",
  "Sequential flow is sufficient for linear document-processing pipelines",
  "rule_engine with explicit rules list produces more consistent risk scores than open-ended LLM reasoning"
]
```

### Failure Patterns

What went wrong during the build and was eventually fixed — things to watch out for:

**How to identify:** Read all FailureTraces from every iteration. Each represents something that failed and was corrected. The pattern is: "[what was tried] → [why it failed] → [what fixed it]".

**Example failure patterns (PS-08):**
```json
[
  "Initial spec used pdf_parser_pymupdf for scanned documents but it has no OCR — added ocr_tesseract as fallback after Critic caught it",
  "First build passed transactions as keyword arg but tool expected positional — fixed parameter binding in tools.py",
  "financial_calculator initially produced raw numbers without labels — added post-processing to structure output as labeled dict"
]
```

### Anti-Patterns

Patterns that should be AVOIDED in future builds — things that reliably cause problems:

**How to identify:** Failures that were spec-level (not just code bugs). Design decisions that the Architect had to fundamentally rethink. Tool selections that couldn't work for structural reasons.

**Example anti-patterns (PS-08):**
```json
[
  "Do not assign pdf_parser_pymupdf as sole extraction tool when requirements include scanned documents — it has no OCR capability",
  "Do not assume LLM text output can be directly parsed as structured data without explicit format conversion step",
  "Do not use 'skip' error handling for agents whose output is required by downstream agents — causes silent data loss"
]
```

### Lessons Learned

Free-form insights that don't fit neatly into success/failure/anti categories:

```json
[
  "Loan underwriting domain benefits from explicit rule definitions rather than open-ended reasoning",
  "Bank statement formats vary widely — extraction confidence scoring is essential for quality gating",
  "Sequential flow was sufficient here, but a parallel flow (extract + analyze multiple statements) would scale better"
]
```

## Step 3: Generate Requirements Summary

The requirements summary is what gets embedded in Chroma for RAG retrieval. It needs to capture the ESSENCE of the requirements in a way that similar future requirements will match against it.

```python
# Not the full RequirementsDoc — a dense summary for embedding
requirements_summary = f"""
Domain: {state["requirements"].domain}
Task: {summarize_process_steps(state["requirements"].process_steps)}
Input types: {[i.format for i in state["requirements"].inputs]}
Output types: {[o.format for o in state["requirements"].outputs]}
Key constraints: {state["requirements"].constraints}
"""
```

**Good summary:** "Loan underwriting domain. Process bank statement PDFs (including scanned) to produce risk score (0-1) and markdown report. Steps: extract text, parse transactions, calculate financial metrics (DTI, income stability), assess risk. Constraints: under 2 minutes, no external APIs."

**Bad summary:** "Build an agent that processes documents" (too vague — everything matches).

## Step 4: Write to Chroma Collections

### Collection: `spec_patterns`

**What:** The validated spec + its outcome. Future Architects query this to find structural reference for similar requirements.

```python
# Document = requirements_summary (for embedding match)
# Metadata = outcome, framework, tools, iteration count
# Embedded object = spec_snapshot + test_results summary

chroma_client.get_or_create_collection("spec_patterns").add(
    documents=[build_outcome.requirements_summary],
    metadatas=[{
        "domain": build_outcome.domain,
        "outcome": build_outcome.outcome,
        "framework": build_outcome.framework_used,
        "tools": json.dumps(build_outcome.tools_used),
        "iterations": build_outcome.iterations_needed,
        "requirements_hash": build_outcome.requirements_hash
    }],
    ids=[f"spec_{build_outcome.requirements_hash}_{timestamp}"]
)
```

**Only write successful or partially successful specs.** Failed specs go to anti_patterns, not spec_patterns. An Architect should never use a failed spec as structural reference.

### Collection: `anti_patterns`

**What:** Patterns that caused failures. Future Architects query this to check "has this pattern failed before?"

```python
for anti_pattern in build_outcome.anti_patterns:
    chroma_client.get_or_create_collection("anti_patterns").add(
        documents=[anti_pattern],
        metadatas=[{
            "domain": build_outcome.domain,
            "severity": "high",  # anti-patterns are always high severity
            "source_build": build_outcome.requirements_hash
        }],
        ids=[f"anti_{hash(anti_pattern)}_{timestamp}"]
    )
```

**Write ALL anti-patterns, regardless of build outcome.** Even successful builds may have encountered anti-patterns that were corrected — those are still valuable.

### Collection: `domain_insights`

**What:** Domain-specific learnings that help future Elicitors and Architects. Not spec-specific — generalizable domain knowledge.

```python
for lesson in build_outcome.lessons_learned:
    chroma_client.get_or_create_collection("domain_insights").add(
        documents=[lesson],
        metadatas=[{
            "domain": build_outcome.domain,
            "source_build": build_outcome.requirements_hash,
            "outcome": build_outcome.outcome
        }],
        ids=[f"insight_{hash(lesson)}_{timestamp}"]
    )
```

### Collection: `tool_schemas` — Updates (not writes)

The Learner doesn't add tools, but it updates existing tool records:
- Add to `compatible_with` if two tools worked well together in this build
- Add to `incompatible_with` if a tool combination caused failures
- These fields grow over time through usage data

```python
# If pdf_parser_pymupdf and json_transformer worked well together:
tool_record = tool_collection.get(where={"id": "pdf_parser_pymupdf"})
# Update compatible_with to include "json_transformer"
```

## Outcome Classification Details

### Success
All tests passed. The generated agent works as specified.
- Write to: spec_patterns, anti_patterns (if any were encountered and fixed), domain_insights
- Success patterns extracted
- Spec snapshot stored as positive reference

### Partial Success
Some tests passed, some failed, but max iterations reached.
- Write to: spec_patterns (with partial flag), anti_patterns, domain_insights
- `partial_success_details` documents what worked and what didn't
- Useful for future builds — the successful parts are valid reference

### Failure
No tests passed, or critical infrastructure failure (Docker unavailable, no code generated).
- Write to: anti_patterns, domain_insights (what we learned from failing)
- Do NOT write to spec_patterns — failed specs are not reference material
- Failure patterns are the primary value — they prevent the same mistake in future builds

## Build Report Output

The Learner produces a human-readable build report as the final pipeline output:

```markdown
# Build Report — {spec.metadata.name}

## Outcome: {outcome}

**Domain:** {domain}
**Framework:** {framework_used}
**Total iterations:** {iterations_needed} (spec: {spec_iteration}, build: {build_iteration})
**Time:** {total_time_seconds}s

## Test Results
- Total: {test_results.total}
- Passed: {test_results.passed}
- Failed: {test_results.failed}

## Agents Built
| Agent | Role | Tools |
|-------|------|-------|
{for each agent in spec}

## Patterns Learned

### What Worked
{success_patterns as bullet list}

### What Failed (and was fixed)
{failure_patterns as bullet list}

### Avoid in Future
{anti_patterns as bullet list}

### Domain Insights
{lessons_learned as bullet list}
```

## Prompt Engineering Notes

**System prompt should establish:**
- Role: "You are a build outcome analyst. Your job is to extract generalizable patterns from a completed build — what worked, what failed, and what should be avoided."
- Pattern quality: "Patterns must be specific and actionable. 'Things went wrong' is not a pattern. 'pdf_parser_pymupdf fails on scanned documents because it lacks OCR' is a pattern."
- Generalizability: "Patterns should apply beyond this specific build. 'The financial_calculator function had a bug on line 42' is a code fix, not a pattern. 'Assuming LLM output is structured JSON without explicit format constraints leads to parsing failures' is a pattern."
- Output: "Return a structured BuildOutcome. Every list field must contain at least one entry — if nothing failed, the failure_patterns list should contain 'No failures encountered' rather than being empty."

**Key behaviors to instruct:**
- Extract patterns at the right abstraction level — not too specific (code line numbers) and not too vague (domain descriptions)
- Success patterns should be ACTIONABLE by a future Architect — specific enough to apply
- Anti-patterns should include WHY the pattern fails, not just WHAT failed
- Domain insights should be useful to a future Elicitor working in the same domain

## Error Handling

| Error | Cause | Response |
|-------|-------|----------|
| Chroma unavailable | Service down, connection error | Write BuildOutcome to a local JSON file as fallback. Log that Chroma write failed. Pipeline still completes — learning is deferred, not lost. |
| Duplicate requirements_hash | Same requirements built twice | Append timestamp to ID. Both records are valuable — different builds of the same requirements may produce different outcomes. |
| Empty state fields | Pipeline terminated early | Write what's available. A failed build with only requirements and a partial spec still has lessons (e.g., "these requirements were too vague for the Architect to produce a spec"). |
| Pattern extraction produces nothing | Learner LLM too conservative | Ensure at least minimum patterns: "Build completed successfully with {tools}" for success, or "Build failed at {stage}" for failure. Something is always learnable. |
| Spec snapshot too large for Chroma | Complex spec with many agents | Store spec summary (metadata, agent IDs, tool IDs, flow pattern) instead of full spec. Link to full spec via requirements_hash if needed later. |
