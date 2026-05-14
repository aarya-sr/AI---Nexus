# Architecture Stage

**Agent:** Architect | **Model:** claude-sonnet-4-6 | **Input:** RequirementsDoc + RAG context | **Output:** AgentSpec

The Architect translates validated requirements into a framework-agnostic agent specification. It makes every architectural decision: how many agents, what tools each uses, how they communicate, what framework to target. This is the hardest agent in the pipeline — it carries the most design responsibility.

## Data Models

### ToolSchema (from Chroma Tool Library)

```python
class ToolSchema(BaseModel):
    id: str                       # "pdf_parser_pymupdf"
    name: str                     # "PyMuPDF PDF Parser"
    description: str              # "Extracts text and tables from PDF files"
    category: str                 # "document_extraction"
    accepts: list[str]            # ["pdf"]
    outputs: list[str]            # ["text", "tables"]
    output_format: str            # "json"
    limitations: list[str]        # ["no OCR for scanned documents"]
    dependencies: list[str]       # ["pymupdf>=1.23.0"]
    code_template: str            # actual Python implementation
    compatible_with: list[str]    # tool IDs that work well downstream
    incompatible_with: list[str]  # tool IDs known to conflict
```

### AgentSpec (full output schema)

```yaml
metadata:
  name: string
  domain: string
  framework_target: crewai | langgraph
  created_from_pattern: string | null  # past spec used as base

agents:
  - id: string
    role: string
    goal: string
    backstory: string
    tools: [tool_id]
    reasoning_strategy: react | cot | plan_execute
    receives_from: [agent_id]
    sends_to: [agent_id]

tools:
  - id: string
    library_ref: string          # reference to Tool Schema Library entry
    config: object               # tool-specific configuration
    accepts: [format]
    outputs: [format]

memory:
  strategy: short_term | long_term | shared | none
  shared_keys: [string]         # data shared between agents
  persistence: session | permanent

execution_flow:
  pattern: sequential | parallel | hierarchical | graph
  graph:                         # only if pattern == graph
    nodes: [agent_id]
    edges:
      - from: agent_id
        to: agent_id
        condition: string | null
        data_contract:
          fields: [field_name]
          format: string

error_handling:
  - agent_id: string
    on_failure: retry | fallback | skip | abort
    max_retries: int
    fallback_agent: string | null

io_contracts:
  - agent_id: string
    input_schema:
      fields: [{name: string, type: string, required: bool}]
    output_schema:
      fields: [{name: string, type: string, required: bool}]
```

## Internal Process

7 logical steps (RAG queries run in parallel as sub-steps of Step 1):

```
Step 1: RAG Queries (parallel)
  ├── 1a. Query Past Specs
  ├── 1b. Query Tool Library
  └── 1c. Check Anti-Patterns
              ↓
       merge RAG context
              ↓
Step 2: Task Decomposition
              ↓
Step 3: Tool Matching
              ↓
Step 4: Agent Grouping
              ↓
Step 5: Flow Design
              ↓
Step 6: Memory Design
              ↓
Step 7: Compile AgentSpec
```

### Step 1a: RAG Query — Past Specs

Query Chroma `spec_patterns` collection:
```
"Find specs similar to: [requirements.domain + summary of process_steps]"
```
Returns top-3 past specs with their outcomes (success/failure, iteration count, tools used). The Architect uses successful ones as structural reference — not copying, but understanding what patterns worked for similar domains.

If this is the first build (empty collection), skip. The Architect works from first principles.

### Step 1b: RAG Query — Tool Library

For each process step in RequirementsDoc, query Chroma `tool_schemas` collection:
```
"Find tools that can: [step.description + required capability]"
```
Returns ranked tool options with format compatibility info. The Architect gets multiple options per capability — it must choose based on format chain compatibility (Step 4).

### Step 1c: RAG Query — Anti-Patterns

Query Chroma `anti_patterns` collection:
```
"Has any pattern similar to [domain + proposed tool combination] failed before?"
```
Returns matching anti-patterns with failure descriptions. The Architect must avoid repeating known mistakes.

### Step 2: Task Decomposition

Break requirements into discrete computational tasks. Each task gets tagged:

| Tag | What It Means | Example |
|-----|--------------|---------|
| input_needs | What data format this task consumes | "pdf" |
| output_produces | What data format this task emits | "json" |
| capability | What kind of computation | "text_extraction", "calculation", "reasoning", "generation" |
| is_parallelizable | Can run concurrent with other tasks | true/false |
| depends_on | Which tasks must complete first | [task_ids] |

**PS-08 Example:**

| Task ID | Description | Input | Output | Capability |
|---------|-------------|-------|--------|------------|
| T1 | Extract text from bank statement PDF | pdf | text + tables | text_extraction |
| T2 | Parse transactions into structured data | text | json (transactions) | data_processing |
| T3 | Calculate financial metrics (DTI, income stability) | json (transactions) | json (metrics) | calculation |
| T4 | Assess risk based on metrics and rules | json (metrics) | json (score + reasoning) | reasoning |
| T5 | Generate human-readable risk report | json (score + reasoning) | markdown | generation |

### Step 3: Tool Matching

For each task, select a tool from the RAG results. Selection criteria, in order:

1. **Format compatibility** — the tool's `accepts` must include the task's `input_needs`. The tool's `outputs` must include what the next task's tool `accepts`. This is the format chain — it must be unbroken from start to end.
2. **Capability match** — the tool's `category` matches the task's `capability`.
3. **Limitation check** — the tool's `limitations` don't conflict with requirements. (e.g., if edge case says "handle scanned PDFs," don't select a tool with limitation "no OCR").
4. **Compatibility check** — check `compatible_with` and `incompatible_with` fields against other selected tools.
5. **Dependency weight** — prefer tools with fewer/lighter `dependencies` to keep the Docker image manageable.

**Format chain validation example (PS-08):**
```
bank_statement.pdf → [pdf_parser_pymupdf: accepts pdf, outputs text+tables]
                   → [json_transformer: accepts text, outputs json]
                   → [financial_calculator: accepts json, outputs json]
                   → [rule_engine: accepts json, outputs json]
                   → [report_generator: accepts json, outputs markdown]
```
Every link in the chain has matching formats. If any link breaks (tool A outputs XML, tool B only accepts JSON), the Architect must either:
- Select a different tool
- Insert a format converter tool between them
- Flag it as a spec issue for the Critic to catch (defense in depth)

### Step 4: Agent Grouping

Group tasks into agents based on:

**Cohesion** — related tasks that share domain context should be in the same agent. An agent that extracts data and immediately parses it is more coherent than splitting extraction and parsing across two agents.

**Coupling** — tasks with tight data dependencies (one produces output consumed immediately by the next in a loop) should be in the same agent. Independent task chains become separate agents.

**Rules of thumb:**
- Sequential tasks with tight data coupling → same agent
- Tasks requiring different expertise/tools that don't share data → separate agents
- If one task might need to retry/loop independently → separate agent (so failure doesn't restart the whole group)
- Max 3-4 tools per agent — more than that suggests the agent is doing too much

**PS-08 Example:**

| Agent | Tasks | Role | Tools |
|-------|-------|------|-------|
| Document Processor | T1, T2 | Extract and structure bank statement data | pdf_parser_pymupdf, json_transformer |
| Financial Analyst | T3, T4 | Calculate metrics and assess risk | financial_calculator, rule_engine |
| Report Writer | T5 | Generate human-readable report | report_generator |

### Step 5: Flow Design

Analyze the dependency graph between agents to select the execution pattern:

| Pattern | When | Framework Target |
|---------|------|-----------------|
| **Sequential** | Linear chain, each agent depends on previous | Either (CrewAI simpler) |
| **Parallel** | Independent agent groups that can run concurrently | Either |
| **Hierarchical** | Manager agent delegates to workers, aggregates results | CrewAI (natural fit) |
| **Graph** | Complex branching, conditional paths, cycles | LangGraph (required) |

**Decision logic:**
```python
if any_conditional_edges or any_cycles:
    framework_target = "langgraph"
elif delegation_pattern:  # manager → workers
    framework_target = "crewai"
    pattern = "hierarchical"
elif all_agents_independent:
    pattern = "parallel"
else:
    pattern = "sequential"
    framework_target = "crewai"  # simpler for linear flows
```

### Step 6: Memory Design

Determine what agents need to share and how:

| Strategy | When | Implementation |
|----------|------|---------------|
| **none** | Agents pass data via direct edges, no shared state | Data in edge contracts |
| **short_term** | Agents need to reference recent conversation/context | In-memory state dict |
| **shared** | Multiple agents read/write common data store | LangGraph state or shared dict |
| **long_term** | Agent outcomes inform future runs | Chroma persistence |

Identify `shared_keys` — specific data fields that multiple agents need access to. For PS-08: `extracted_transactions`, `financial_metrics`, `risk_score` might be shared keys if agents need to cross-reference.

### Step 7: Compile AgentSpec

Assemble all decisions into the AgentSpec YAML schema. Every field must be populated. The `io_contracts` section is critical — it defines exactly what each agent receives and produces, field by field. The Tester will generate test cases directly from these contracts.

## Handling Critique Feedback (Loop Re-entry)

When the Architect receives critique feedback (loop from Critic):
1. Read `state["critique"].findings` — every finding with severity "critical"
2. For each critical finding, read `suggested_fix`
3. Apply fixes to the spec — this might mean changing tools, restructuring agents, modifying flow
4. Increment `spec_iteration`
5. Log what changed and why (for the Learner to capture later)
6. Do NOT start from scratch — modify the existing spec

**Warning findings** should be addressed if straightforward, but don't block progression. **Suggestion findings** are optional improvements.

## Prompt Engineering Notes

**System prompt should establish:**
- Role: "You are a system architect designing multi-agent pipelines. Your decisions determine whether the generated system works or fails."
- Context injection: Paste RAG results (past specs, tool options, anti-patterns) into context before the requirements
- Reasoning: "Think through each decision step by step. Explain why you chose each tool, why agents are grouped this way, and why this flow pattern."
- Output format: "Produce a valid AgentSpec YAML. Every field must be populated. The io_contracts section is tested downstream — accuracy matters."
- Constraint: "Only select tools from the provided Tool Library. Do not invent tools that don't exist in the library."

**Key behaviors to instruct:**
- When past specs are provided, explain what you're borrowing and what you're changing
- When anti-patterns match, explicitly state "I'm avoiding [pattern] because [past failure]"
- When tool selection involves trade-offs, document the trade-off in the spec's metadata
- If no tool in the library fits a capability, flag it — don't silently drop the requirement

## Example Output — PS-08 AgentSpec (abbreviated)

```yaml
metadata:
  name: loan_underwriting_copilot
  domain: loan_underwriting
  framework_target: crewai
  created_from_pattern: null

agents:
  - id: document_processor
    role: Bank Statement Data Extractor
    goal: Extract and structure all financial data from bank statement PDFs
    backstory: Expert at parsing financial documents, handles both digital and scanned PDFs
    tools: [pdf_parser_pymupdf, ocr_tesseract, json_transformer]
    reasoning_strategy: cot
    receives_from: []
    sends_to: [financial_analyst]

  - id: financial_analyst
    role: Financial Metrics Calculator and Risk Assessor
    goal: Calculate underwriting metrics and produce a risk score with reasoning
    backstory: Senior underwriter with expertise in DTI analysis, income stability, and fraud detection
    tools: [financial_calculator, rule_engine]
    reasoning_strategy: react
    receives_from: [document_processor]
    sends_to: [report_writer]

  - id: report_writer
    role: Risk Report Generator
    goal: Produce a clear, evidence-based risk assessment report
    backstory: Technical writer specializing in financial risk communication
    tools: [report_generator]
    reasoning_strategy: cot
    receives_from: [financial_analyst]
    sends_to: []

tools:
  - id: pdf_parser_pymupdf
    library_ref: pdf_parser_pymupdf
    config: {extract_tables: true}
    accepts: [pdf]
    outputs: [text, tables]
  - id: ocr_tesseract
    library_ref: ocr_tesseract
    config: {language: "eng", confidence_threshold: 0.6}
    accepts: [image, scanned_pdf]
    outputs: [text]
  # ... remaining tools

memory:
  strategy: short_term
  shared_keys: [extracted_transactions, financial_metrics, risk_score]
  persistence: session

execution_flow:
  pattern: sequential
  graph: null

error_handling:
  - agent_id: document_processor
    on_failure: retry
    max_retries: 2
    fallback_agent: null
  - agent_id: financial_analyst
    on_failure: retry
    max_retries: 1
    fallback_agent: null
  - agent_id: report_writer
    on_failure: retry
    max_retries: 1
    fallback_agent: null

io_contracts:
  - agent_id: document_processor
    input_schema:
      fields:
        - {name: bank_statement_path, type: string, required: true}
        - {name: statement_format, type: string, required: false}
    output_schema:
      fields:
        - {name: transactions, type: "list[dict]", required: true}
        - {name: account_summary, type: dict, required: true}
        - {name: extraction_confidence, type: float, required: true}

  - agent_id: financial_analyst
    input_schema:
      fields:
        - {name: transactions, type: "list[dict]", required: true}
        - {name: account_summary, type: dict, required: true}
    output_schema:
      fields:
        - {name: risk_score, type: float, required: true}
        - {name: risk_factors, type: dict, required: true}
        - {name: reasoning, type: string, required: true}

  - agent_id: report_writer
    input_schema:
      fields:
        - {name: risk_score, type: float, required: true}
        - {name: risk_factors, type: dict, required: true}
        - {name: reasoning, type: string, required: true}
    output_schema:
      fields:
        - {name: report_markdown, type: string, required: true}
        - {name: executive_summary, type: string, required: true}
```

## Error Handling

| Error | Cause | Response |
|-------|-------|----------|
| No tools match a required capability | Tool library is incomplete for this domain | Flag the missing capability explicitly in the spec. Do NOT silently drop the requirement. Output includes a `missing_tools` field listing what's needed. Builder will fail, but the failure will be traceable. |
| RAG returns no past specs | First build, empty collection | Proceed from first principles. Log that no prior art was available. |
| Anti-pattern match but no alternative | Known bad pattern, but it's the only option | Use it anyway, but flag in spec metadata: "Known risk: [anti-pattern]. Mitigation: [what you're doing differently]." Critic will examine this. |
| Format chain breaks | Tool A outputs format X, Tool B needs format Y | Insert a format converter tool (e.g., json_transformer). If no converter exists in the library, flag as missing tool. |
| Too many tasks for reasonable agent count | Requirements produce 15+ discrete tasks | Group aggressively. Aim for 3-5 agents max. If tasks can't be reasonably grouped, flag to the Critic that the scope may be too large for a single agent system. |
| Conflicting requirements | "Must be fast" + "Must use OCR on every page" | Surface the conflict in the spec. Let the Critic and human checkpoint resolve the trade-off. |
| Critique loop re-entry with contradictory fixes | Critic says "add tool X" and "remove dependency on X" | Address the most severe finding first. If truly contradictory, flag in spec and let the next Critic iteration resolve. |
