# Test Stage

**Agent:** Tester | **Model:** gpt-4o-mini | **Input:** CodeBundle + AgentSpec | **Output:** TestReport + FailureTraces

The Tester runs the generated agent code in a Docker sandbox, validates output against the spec's io_contracts, and traces failures back to either code-level bugs (Builder fix) or spec-level design flaws (Architect fix). The Tester does not fix code — it diagnoses problems and routes them to the right fixer.

## Data Models

```python
class TestCase(BaseModel):
    name: str                        # "test_bank_statement_processing"
    description: str                 # what this test validates
    input_data: dict                 # sample input (synthetic)
    expected_output_schema: dict     # JSON schema the output must match
    quality_checks: list[str]        # human-readable assertions
    timeout: int                     # seconds (default: DOCKER_TIMEOUT)

class TestReport(BaseModel):
    total: int                       # total test cases
    passed: int
    failed: int
    errors: int                      # crashes vs wrong output
    all_passed: bool                 # convenience flag
    results: list[TestResult]

class TestResult(BaseModel):
    test_name: str
    status: Literal["passed", "failed", "error"]
    duration_seconds: float
    stdout: str                      # captured container stdout
    stderr: str                      # captured container stderr
    exit_code: int
    output_parsed: dict | None       # parsed output if parseable
    validation_details: str          # what passed/failed and why

class FailureTrace(BaseModel):
    test_name: str
    error_type: Literal["crash", "wrong_output", "missing_field", "quality_fail"]
    raw_error: str                   # actual error message or bad output
    failing_agent: str               # which agent in the generated pipeline
    root_cause_level: Literal["code", "spec"]
    root_cause_analysis: str         # "Agent 2 received XML but tool expects JSON"
    spec_decision_responsible: str   # "spec.tools[1].library_ref = xml_parser"
    suggested_fix: str               # "Change to json_parser or add format converter"
```

## Internal Process

```
Generate Test Cases (from spec.io_contracts)
       ↓
Run Docker Container (mount CodeBundle into pre-built frankenstein-runner image)
       ↓
┌──────────────────────────────────────────────┐
│  For each test case:                         │
│    → Mount test input into container         │
│    → Run container with timeout              │
│    → Capture stdout, stderr, exit code       │
│    → Parse output                            │
│    → Validate against expected schema        │
│    → Run quality checks                      │
│    → Record TestResult                       │
└──────────────────────────────────────────────┘
       ↓
Aggregate TestReport
       ↓
For each failure: Generate FailureTrace
       ↓
Route: all passed → Learner | failures → Builder or Architect
```

## Step 1: Test Case Generation

The Tester reads `spec.io_contracts` and generates test cases for each agent AND for the end-to-end pipeline.

### Per-Agent Tests

For each agent's io_contract:
1. Generate synthetic input matching `input_schema` (realistic data for the domain)
2. Define expected output matching `output_schema` (every required field present, correct types)
3. Add quality checks from `requirements.quality_criteria`

### End-to-End Test

Test the full pipeline from entry point input to final output:
1. Generate a complete synthetic input (e.g., a synthetic bank statement for PS-08)
2. Expected output: all final output fields present with correct types
3. Quality checks: domain-specific assertions from requirements

### Synthetic Input Generation

For hackathon scope, test inputs are LLM-generated (synthetic):
- The Tester uses its LLM (gpt-4o-mini) to generate realistic test data based on the domain and requirements
- For PS-08: generate a synthetic bank statement text (not an actual PDF for hackathon — text representation)
- For production: would use real sample data provided by the human

**Synthetic input rules:**
- Must match the `input_schema` exactly (right fields, right types)
- Must be domain-realistic (not lorem ipsum — actual transaction data for a bank statement)
- Include edge case inputs if requirements specify edge cases
- Generate at least 1 happy-path test + 1 edge-case test per agent

### Example Test Cases — PS-08

```python
# Happy path: standard bank statement
TestCase(
    name="test_standard_bank_statement",
    description="Process a standard 3-month bank statement with typical transactions",
    input_data={
        "bank_statement_path": "/test_data/standard_statement.txt",
        "bank_statement_content": "Chase Bank Statement\nAccount: ****1234\nPeriod: Jan-Mar 2024\n\nDate | Description | Amount\n01/05 | Payroll Deposit | +4,500.00\n01/07 | Rent Payment | -1,800.00\n01/10 | Grocery Store | -125.50\n..."
    },
    expected_output_schema={
        "type": "object",
        "required": ["risk_score", "report_markdown", "executive_summary"],
        "properties": {
            "risk_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "report_markdown": {"type": "string", "minLength": 100},
            "executive_summary": {"type": "string", "minLength": 50}
        }
    },
    quality_checks=[
        "risk_score is between 0.0 and 1.0",
        "report_markdown mentions income stability",
        "report_markdown mentions debt-to-income ratio",
        "executive_summary is non-empty",
        "report_markdown contains at least 3 sections"
    ],
    timeout=60
)

# Edge case: minimal transaction history
TestCase(
    name="test_minimal_history",
    description="Process a statement with less than 1 month of history",
    input_data={
        "bank_statement_path": "/test_data/minimal_statement.txt",
        "bank_statement_content": "Chase Bank Statement\nAccount: ****5678\nPeriod: Mar 2024\n\nDate | Description | Amount\n03/01 | Payroll Deposit | +3,200.00\n03/15 | Transfer Out | -500.00\n"
    },
    expected_output_schema={
        "type": "object",
        "required": ["risk_score", "report_markdown"],
        "properties": {
            "risk_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "report_markdown": {"type": "string"}
        }
    },
    quality_checks=[
        "risk_score is between 0.0 and 1.0",
        "report_markdown mentions limited data or insufficient history",
        "report_markdown flags uncertainty or low confidence"
    ],
    timeout=60
)
```

## Step 2: Docker Execution

The Tester does NOT build a Docker image. It mounts the generated code into the pre-built `frankenstein-runner` base image (Python 3.11 + CrewAI + LangGraph + common deps pre-installed).

### Container Launch

```python
# Using Docker SDK for Python
import docker

client = docker.from_env()

# Build from frankenstein-runner base image
# Mount generated_agent/ into /agent
container = client.containers.run(
    image="frankenstein-runner",
    command=f"python main.py {test_input_path}",
    volumes={
        str(generated_agent_path): {"bind": "/agent", "mode": "rw"},
        str(test_data_path): {"bind": "/test_data", "mode": "ro"}
    },
    working_dir="/agent",
    environment={
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
    },
    detach=True,
    mem_limit="512m",        # memory cap
    network_mode="bridge"     # allow outbound for LLM API calls
)
```

### Execution and Capture

```python
# Wait for completion with timeout
try:
    result = container.wait(timeout=test_case.timeout)
    exit_code = result["StatusCode"]
    stdout = container.logs(stdout=True, stderr=False).decode()
    stderr = container.logs(stdout=False, stderr=True).decode()
except requests.exceptions.ReadTimeout:
    container.kill()
    exit_code = -1
    stdout = ""
    stderr = f"Container timed out after {test_case.timeout}s"
finally:
    container.remove(force=True)
```

### Execution Rules

- Each test case runs in a FRESH container — no state leaks between tests
- Timeout is enforced strictly — container is killed, not asked nicely
- Memory is capped at 512MB — prevents runaway processes
- Network access is allowed (LLM API calls) but could be restricted for offline tests
- Test data is mounted read-only — generated code cannot modify test inputs

## Step 3: Output Validation

### Parse Output

```python
# Try to parse stdout as JSON
try:
    output = json.loads(stdout)
    output_parsed = output
except json.JSONDecodeError:
    # Try to extract JSON from mixed output
    # Look for first { ... } block in stdout
    # If no JSON found, output_parsed = None
    output_parsed = None
```

### Schema Validation

```python
import jsonschema

try:
    jsonschema.validate(output_parsed, test_case.expected_output_schema)
    schema_valid = True
except jsonschema.ValidationError as e:
    schema_valid = False
    schema_error = str(e)
```

### Quality Checks

Each quality check in `test_case.quality_checks` is a human-readable assertion. The Tester's LLM interprets and validates each:

```python
# Example quality check: "risk_score is between 0.0 and 1.0"
# Tester checks: output["risk_score"] >= 0.0 and output["risk_score"] <= 1.0

# Example quality check: "report_markdown mentions income stability"
# Tester checks: "income stability" in output["report_markdown"].lower()
#   or uses LLM to semantically verify the concept is present
```

Quality checks that require semantic understanding (not just field presence) use the Tester's LLM for validation. Simple type/range checks are done programmatically.

## Step 4: Failure Trace Generation

For each failed test, the Tester generates a FailureTrace. This is the most important output — it determines routing.

### Error Type Classification

| Exit Condition | error_type | Typical Cause |
|---------------|------------|---------------|
| Non-zero exit code, Python traceback in stderr | `crash` | Import error, runtime exception, tool failure |
| Zero exit, output doesn't match schema | `wrong_output` | Code produces wrong structure |
| Zero exit, required field missing from output | `missing_field` | Agent didn't produce expected data |
| Zero exit, schema valid, quality check fails | `quality_fail` | Output technically correct but semantically wrong |

### Root Cause Level Classification

This is the critical routing decision. The Tester must determine whether the failure is fixable by the Builder (code-level) or requires the Architect to redesign (spec-level).

**Code-level failures (`root_cause_level = "code"`):**
- Syntax errors in generated code
- Import errors (wrong package name, missing dependency)
- Runtime exceptions in tool implementations (null pointer, type error)
- Output formatting issues (producing string instead of JSON)
- Off-by-one errors, wrong variable references
- Tool binding issues (calling tool with wrong arguments)

**Spec-level failures (`root_cause_level = "spec"`):**
- Agent receives data in format it can't process (format chain broken in spec)
- Tool genuinely cannot perform the task assigned to it (wrong tool selected)
- Missing agent — no agent handles a required step
- io_contract mismatch — spec says agent produces X but the design makes it impossible
- Circular dependency causing infinite loop (should have been caught by Critic)
- Edge case not handled because spec didn't account for it

### Root Cause Analysis Process

```
1. Read the error/output
2. Identify which agent in the generated pipeline failed
3. Trace backward:
   - What input did the failing agent receive?
   - Was the input in the expected format? (if no → spec-level, format chain issue)
   - Did the tool behave as documented? (if no → code-level, tool binding issue)
   - Did the agent have the right tools for the task? (if no → spec-level, wrong tool)
4. Classify root_cause_level
5. Identify the specific spec decision or code section responsible
6. Suggest a fix appropriate to the level
```

### Example FailureTrace — PS-08

```json
{
  "test_name": "test_standard_bank_statement",
  "error_type": "crash",
  "raw_error": "TypeError: financial_calculator() got an unexpected keyword argument 'transactions'. Expected 'data' parameter.",
  "failing_agent": "financial_analyst",
  "root_cause_level": "code",
  "root_cause_analysis": "The tool binding in tools.py passes the parameter as 'transactions' but the financial_calculator code_template expects parameter named 'data'. This is a code-level binding error, not a spec issue — the spec correctly identifies the data flow.",
  "spec_decision_responsible": "N/A — code-level issue in tools.py tool binding",
  "suggested_fix": "In tools.py, change the financial_calculator call to pass 'data=transactions' instead of 'transactions=transactions'"
}
```

```json
{
  "test_name": "test_standard_bank_statement",
  "error_type": "wrong_output",
  "raw_error": "Output missing required field 'risk_factors'. Got: {'risk_score': 0.35, 'reasoning': '...'}",
  "failing_agent": "financial_analyst",
  "root_cause_level": "spec",
  "root_cause_analysis": "The spec's io_contract for financial_analyst requires output field 'risk_factors' (type: dict, required: true), but the rule_engine tool only produces 'reasoning' (string). The tool cannot produce structured risk_factors — it outputs free-text reasoning. The spec assumed the tool could produce structured data it cannot.",
  "spec_decision_responsible": "spec.io_contracts[financial_analyst].output_schema.risk_factors — requires structured dict, but spec.tools[rule_engine] only outputs text reasoning",
  "suggested_fix": "Either: (1) change io_contract to accept 'reasoning: string' instead of 'risk_factors: dict', or (2) add a post-processing step that structures the reasoning into a dict"
}
```

## Routing Logic

```python
def route_after_test(state: FrankensteinState) -> str:
    if state["test_results"].all_passed:
        return "learner"

    if state["build_iteration"] >= MAX_BUILD_ITERATIONS:
        return "learner"  # partial success, store what we learned

    # Analyze failures — check if ANY are spec-level
    for trace in state["failure_traces"]:
        if trace.root_cause_level == "spec":
            return "architect"  # spec-level fix needed, re-enter architect

    # All failures are code-level
    return "builder"  # code fix sufficient
```

**Routing priority:**
1. All passed → Learner (done)
2. Max iterations → Learner (partial success, record failure patterns)
3. Any spec-level failure → Architect (even if some failures are code-level — spec fix first)
4. All code-level → Builder (quickest fix path)

**Why spec-level routes to Architect even with mixed failures:** If the spec has a design flaw, fixing code is wasted effort — the Builder will just regenerate the same broken pattern. Fix the spec first, then rebuild.

## Prompt Engineering Notes

**System prompt should establish:**
- Role: "You are a QA engineer testing generated agent code. Your job is to run tests, validate output, and precisely diagnose failures."
- Diagnostic discipline: "When a test fails, trace the root cause methodically. Don't guess — follow the data path from input to failure point."
- Root cause precision: "Classifying root_cause_level correctly is critical. A code-level failure sent to the Architect wastes an iteration. A spec-level failure sent to the Builder wastes an iteration. Get it right."
- Output: "Return structured TestReport and FailureTraces. Every failure must have specific evidence."

**Key behaviors to instruct:**
- Generate realistic test data. "test_input_1" is not realistic. A synthetic bank statement with actual-looking transactions is realistic.
- When output is partially correct (some fields right, some wrong), validate each field independently. Don't mark the entire test as failed for one missing field.
- Quality checks should be conservative — if uncertain whether output meets a semantic quality check, flag as failed with explanation. False negatives (missing a real issue) are worse than false positives (flagging something that's fine).
- Include both stdout AND stderr in test results — stderr often contains the real diagnostic info.

## Error Handling

| Error | Cause | Response |
|-------|-------|----------|
| Docker image build fails | Missing base image, dependency conflict | Check frankenstein-runner image exists. If missing, provide instructions to build. If deps conflict, flag in FailureTrace as code-level (requirements.txt issue). |
| Container crashes immediately | Import error, missing env var | Capture stderr. Usually code-level: wrong import or missing API key in environment. |
| Container hangs (timeout) | Infinite loop, deadlock, waiting for input | Kill container. Classify: if caused by circular agent dependency → spec-level. If caused by tool hanging → code-level. |
| Output is not JSON | Code prints debug info, wrong output format | Attempt to extract JSON from mixed output. If no JSON found, classify as code-level (output formatting issue). |
| All tests fail identically | Fundamental issue in generated code | Likely one root cause. Generate one FailureTrace with compound evidence, not N identical traces. |
| Docker SDK unavailable | Docker not installed/running | Surface error immediately: "Docker is required for testing. Ensure Docker daemon is running." Cannot proceed without Docker. |
| API keys not available in container | Environment not passed through | Code-level fix: ensure environment variables are passed in docker run command. |
