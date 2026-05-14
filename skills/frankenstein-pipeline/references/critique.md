# Critique Stage

**Agent:** Critic | **Model:** gpt-4o (deliberately different family from Architect) | **Input:** AgentSpec + RequirementsDoc (from state) | **Output:** CritiqueReport

The Critic reads from the full pipeline state. While AgentSpec is the primary target of review, RequirementsDoc is needed for context — particularly for Tool Validation (checking limitations against requirements edge cases) and Dependency Completeness (verifying all requirements are covered).

The Critic is an adversarial reviewer. Its job is to ATTACK the spec, not validate it. It runs six independent attack vectors in parallel, each probing a different class of failure. The Critic does not suggest architecture — it finds holes. The Architect fixes them.

**Why a different model family:** The Architect (Claude) and Critic (GPT-4o) use different model families because same-model review shares blind spots. If Claude designed it and Claude reviews it, both will miss the same class of errors. GPT-4o thinks differently — different training, different failure modes, different strengths. This cross-model adversarial review is a core architectural differentiator.

## Data Models

```python
class Finding(BaseModel):
    vector: str                    # which attack vector found this
    severity: Literal["critical", "warning", "suggestion"]
    description: str               # what's wrong
    location: str                  # which agent/edge/tool is affected
    evidence: str                  # specific spec values that conflict
    suggested_fix: str             # what the Architect should change

class CritiqueReport(BaseModel):
    findings: list[Finding]
    summary: str                   # executive summary of spec health
    iteration: int                 # which architect-critic loop this is
```

### Severity Definitions

| Severity | Meaning | Effect |
|----------|---------|--------|
| **critical** | Spec will produce non-functional code. Must fix before proceeding. | Triggers Architect loop if under MAX_SPEC_ITERATIONS |
| **warning** | Spec will produce functional but fragile/suboptimal code. Should fix. | Does not block. Surfaced to human at checkpoint. |
| **suggestion** | Improvement opportunity. Nice to have. | Does not block. Surfaced to human at checkpoint. |

## The Six Attack Vectors

Each vector runs independently. They can execute in parallel — no dependencies between them.

---

### Vector 1: Format Compatibility

**What it checks:** Does Agent A's output format match Agent B's input format, across every edge in the execution graph?

**How:**
1. Walk every edge in `execution_flow.graph.edges` (or infer edges from `agents[].sends_to`)
2. For each edge, find the sending agent's `io_contracts.output_schema` and the receiving agent's `io_contracts.input_schema`
3. Compare field types: does the sender produce every field the receiver requires?
4. Check format consistency: if sender outputs `text` but receiver expects `json`, that's a format mismatch

**What to look for:**
- Type mismatches: sender outputs `string`, receiver expects `list[dict]`
- Missing required fields: receiver needs `transactions` but sender doesn't produce it
- Format gaps: no converter between incompatible formats
- Implicit conversions: spec assumes a tool handles format conversion that it doesn't

**Example finding (PS-08):**
```json
{
  "vector": "format_compatibility",
  "severity": "critical",
  "description": "document_processor outputs 'text' but financial_analyst input requires 'list[dict]' for transactions field",
  "location": "edge: document_processor → financial_analyst",
  "evidence": "document_processor.output_schema.transactions: type='text', financial_analyst.input_schema.transactions: type='list[dict]'",
  "suggested_fix": "Add json_transformer tool to document_processor, or add a parsing step that converts extracted text to structured transaction list"
}
```

---

### Vector 2: Tool Validation

**What it checks:** Does each tool actually support the data format it's being asked to process?

**How:**
1. For each tool in `spec.tools`, find its `library_ref` in the Tool Schema Library
2. Compare the tool's `accepts` field against the data it will actually receive (traced from upstream agent outputs)
3. Compare the tool's `outputs` field against what the spec claims the agent will produce
4. Check `limitations` against requirements — does any requirement violate a tool's stated limitation?

**What to look for:**
- Tool assigned to process a format it doesn't accept
- Tool's limitations conflict with requirements (e.g., "no OCR" tool assigned to process scanned PDFs)
- Tool's actual output format differs from what the spec claims
- Tool's `incompatible_with` list includes another tool in the same agent

**Example finding:**
```json
{
  "vector": "tool_validation",
  "severity": "critical",
  "description": "pdf_parser_pymupdf has limitation 'no OCR for scanned documents' but requirements include scanned PDF handling",
  "location": "agent: document_processor, tool: pdf_parser_pymupdf",
  "evidence": "tool.limitations=['no OCR for scanned documents'], requirements.edge_cases includes 'Scanned PDF with poor image quality'",
  "suggested_fix": "Add ocr_tesseract as a fallback tool in document_processor with conditional routing based on document type"
}
```

---

### Vector 3: Dead-End Analysis

**What it checks:** Can any agent fail without being caught? Are there execution paths that silently drop data or hang?

**How:**
1. Check every agent's `error_handling` config in the spec
2. Flag any agent with `on_failure: null` or missing error handling entirely
3. Check for agents that produce output but nothing consumes it (dead-end data)
4. Check for agents with `sends_to: []` that are NOT the final agent in the pipeline
5. Verify that fallback agents actually exist if referenced

**What to look for:**
- Agent with no error handling at all — if it crashes, the whole pipeline hangs
- Agent configured to `skip` on failure, but downstream agents require its output
- Fallback agent that doesn't exist in the spec
- Retry configured but max_retries = 0
- Agent produces output that nothing reads (wasted computation, possible missing edge)

**Example finding:**
```json
{
  "vector": "dead_end_analysis",
  "severity": "warning",
  "description": "document_processor.on_failure is 'retry' with max_retries=2, but no fallback defined. If retry exhausted, pipeline hangs.",
  "location": "agent: document_processor, error_handling",
  "evidence": "on_failure='retry', max_retries=2, fallback_agent=null",
  "suggested_fix": "Add fallback_agent or change on_failure to 'abort' with clear error message after retries exhausted"
}
```

---

### Vector 4: Dependency Completeness

**What it checks:** Does every agent receive ALL the fields it needs from upstream agents?

**How:**
1. For each agent, collect all `input_schema.fields` where `required: true`
2. Trace each required field back to upstream agents' `output_schema.fields`
3. If a required field is not produced by any upstream agent, that's a missing dependency
4. Check transitive dependencies — if Agent C needs data that Agent A produces but Agent B (the intermediary) doesn't pass through

**What to look for:**
- Required input field with no upstream source
- Field name mismatch (upstream calls it `tx_data`, downstream expects `transactions`)
- Data transformation gap (upstream outputs raw data, downstream expects computed metrics)
- Transitive loss (data produced by A, passed through B, but B doesn't include it in output)

**Example finding:**
```json
{
  "vector": "dependency_completeness",
  "severity": "critical",
  "description": "financial_analyst requires 'account_summary' (required=true) but document_processor's output_schema doesn't include this field",
  "location": "agent: financial_analyst, field: account_summary",
  "evidence": "financial_analyst.input_schema includes {name: 'account_summary', required: true}, document_processor.output_schema has no 'account_summary' field",
  "suggested_fix": "Add 'account_summary' field to document_processor's output_schema, or derive it within financial_analyst from transactions data"
}
```

---

### Vector 5: Resource Conflicts

**What it checks:** Do parallel agents write to the same shared memory keys? Can concurrent execution cause race conditions?

**How:**
1. Identify which agents run in parallel (from `execution_flow.pattern` and edge analysis)
2. For each parallel agent group, check `memory.shared_keys`
3. If two parallel agents write to the same shared key, that's a resource conflict
4. Check if any agent reads a shared key that another parallel agent writes to (read-after-write hazard)

**What to look for:**
- Two parallel agents writing to the same shared key
- Read-after-write on shared state between concurrent agents
- File system conflicts (two agents writing to the same output path)
- API rate limit conflicts (two agents hitting the same external API concurrently)

**Note:** For sequential pipelines (like PS-08), this vector will often produce zero findings. That's expected. It becomes critical for parallel execution patterns.

**Example finding (hypothetical parallel pipeline):**
```json
{
  "vector": "resource_conflicts",
  "severity": "critical",
  "description": "agents 'data_fetcher_a' and 'data_fetcher_b' both run in parallel and write to shared_key 'raw_data'",
  "location": "parallel group: [data_fetcher_a, data_fetcher_b], shared_key: raw_data",
  "evidence": "execution_flow.pattern='parallel', memory.shared_keys includes 'raw_data', both agents list 'raw_data' in output fields",
  "suggested_fix": "Use agent-specific keys ('raw_data_a', 'raw_data_b') and merge downstream, or serialize the agents"
}
```

---

### Vector 6: Circular Dependencies

**What it checks:** Does the execution graph contain cycles that would cause infinite loops?

**How:**
1. Build a directed graph from `execution_flow.graph.edges` (or from `agents[].sends_to`)
2. Run topological sort on the graph
3. If topological sort fails, there's a cycle — identify which agents form the cycle
4. Check conditional edges — a cycle is acceptable ONLY if the conditional edge has a guaranteed termination condition (e.g., counter-based loop with a max)

**What to look for:**
- Unconditional cycles (A → B → A with no exit condition)
- Conditional cycles without clear termination (loop condition that could theoretically never be met)
- Self-loops (agent sends_to itself)
- Cycles that span more than 3 agents (complex cycles are harder to reason about)

**Note:** Most simple pipelines won't have cycles. Graph-based LangGraph specs with conditional routing are where cycles appear.

**Example finding:**
```json
{
  "vector": "circular_dependencies",
  "severity": "critical",
  "description": "Unconditional cycle detected: analyst → validator → analyst with no termination condition",
  "location": "agents: [analyst, validator], edges forming cycle",
  "evidence": "analyst.sends_to=['validator'], validator.sends_to=['analyst'], no conditional edge with termination",
  "suggested_fix": "Add iteration counter and max_iterations condition to the validator → analyst edge, or restructure as a single agent with internal validation loop"
}
```

---

## Aggregation and Reporting

After all six vectors complete:
1. Merge all findings into a single list
2. Sort by severity: critical → warning → suggestion
3. Generate executive summary: "X critical findings, Y warnings, Z suggestions. [One-sentence assessment of spec health]."
4. Set `iteration` to current `state["spec_iteration"]`

## Loop Mechanics

The Critic's output determines routing:

```python
def route_after_critique(state: FrankensteinState) -> str:
    criticals = [f for f in state["critique"].findings if f.severity == "critical"]
    if len(criticals) > 0 and state["spec_iteration"] < MAX_SPEC_ITERATIONS:
        return "architect"  # loop back with critique attached
    return "human_review_spec"  # no criticals, or max iterations reached
```

**On loop back to Architect:**
- All findings (including warnings and suggestions) are attached to state
- The Architect MUST address every critical finding
- The Architect SHOULD address warnings if straightforward
- The Architect MAY ignore suggestions
- spec_iteration increments

**On second+ critique iterations:**
- The Critic checks for NEW issues introduced by the revision
- The Critic verifies that previously critical findings were actually addressed
- If a "fixed" critical reappears, severity escalates and the finding notes "previously flagged, not resolved"

**Max iterations reached with remaining criticals:**
- Proceed to human checkpoint anyway
- Surface remaining criticals prominently — the human makes the call
- Build may fail if criticals aren't resolved, but the human accepted the risk

## Prompt Engineering Notes

**System prompt should establish:**
- Role: "You are an adversarial spec reviewer. Your job is to find flaws that will cause the generated agent to fail. You are not here to validate — you are here to attack."
- Mindset: "Assume the spec has bugs. Your job is to find them. A clean review is suspicious — look harder."
- Scope: "Only critique the spec against its own contracts and the tool library. Do not suggest architectural alternatives unless the current architecture is fundamentally broken."
- Structure: "Output a CritiqueReport with findings. Each finding must have specific evidence from the spec — no vague concerns."
- Output format: "Respond with structured JSON matching the CritiqueReport schema."

**Key behaviors to instruct:**
- Be specific. "There might be format issues" is not a finding. "document_processor outputs text but financial_analyst expects list[dict]" is a finding.
- Include evidence from the spec — quote the exact field values that conflict
- Provide actionable suggested_fix — not "reconsider the design" but "add json_transformer tool to convert text output to structured JSON"
- Don't critique style or naming — only structural/functional issues
- On second+ iterations: explicitly state which previous findings were resolved and which remain

## Error Handling

| Error | Cause | Response |
|-------|-------|----------|
| Critic produces no findings | Spec is clean, or Critic is too lenient | On first iteration, this is suspicious. Add a meta-finding: "suggestion" severity, "No issues found — spec appears sound. Recommend human review of io_contracts for domain accuracy." |
| Critic finds 10+ criticals | Spec is fundamentally broken | Group related findings. Suggest the Architect focus on the 3 highest-impact criticals first. Don't overwhelm with fixes that depend on other fixes. |
| Critic flags a feature as a bug | Misunderstanding of requirements | Include the requirement context in the finding so the Architect can determine if it's a real issue or an intentional design choice. |
| LLM hallucinates a tool limitation | Claims tool X can't do Y, but it can | Every finding must reference specific spec values as evidence. If evidence is vague or fabricated, the Architect can dismiss with rationale. |
| Critique loop hits MAX_SPEC_ITERATIONS | Can't converge | Proceed to human checkpoint. Show remaining criticals prominently. Log iteration history for the Learner. |
