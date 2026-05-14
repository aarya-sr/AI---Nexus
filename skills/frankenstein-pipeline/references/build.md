# Build Stage

**Agent:** Builder | **Model:** claude-sonnet-4-6 | **Input:** validated AgentSpec | **Output:** CodeBundle (generated_agent/ directory)

The Builder compiles a validated AgentSpec into runnable code. It does NOT invent architecture — every decision was already made by the Architect and validated by the Critic. The Builder is a compiler: spec in, code out. Template-driven, not free-form generation.

## Data Models

```python
class CodeBundle(BaseModel):
    files: dict[str, str]          # filename → file content
    framework: str                 # "crewai" or "langgraph"
    entry_point: str               # "main.py"
    dependencies: list[str]        # pip packages
    validation_passed: bool        # post-generation validation
    validation_errors: list[str]   # any issues found
```

### Generated Project Structure

```
generated_agent/
├── main.py                # entry point — runs the pipeline
├── agents.py              # agent definitions (roles, goals, backstories)
├── tools.py               # tool implementations from code_templates
├── orchestration.py       # CrewAI Crew or LangGraph StateGraph
├── config.yaml            # agent and tool configuration
├── requirements.txt       # Python dependencies
└── tests/
    └── test_pipeline.py   # auto-generated test stubs from io_contracts
```

## Internal Process

```
Read AgentSpec
       ↓
Select Framework Compiler (CrewAI or LangGraph)
       ↓
┌──────────────────────────────────────────────┐
│  For each agent in spec:                     │
│    → Generate agent definition               │
│  For each tool in spec:                      │
│    → Pull code_template from Tool Library    │
│    → Generate tool binding                   │
│  Generate orchestration code                 │
│  Generate entry point                        │
│  Generate config.yaml                        │
│  Generate requirements.txt                   │
│  Generate test stubs                         │
└──────────────────────────────────────────────┘
       ↓
Assemble CodeBundle
       ↓
Run 3-Step Validation
       ↓
Output CodeBundle (pass or fail with errors)
```

## Framework Compilers

### CrewAI Compiler

Used when `spec.execution_flow.pattern` is `sequential` or `hierarchical`.

**Agent mapping:**
```python
# From spec:
#   agent.id = "document_processor"
#   agent.role = "Bank Statement Data Extractor"
#   agent.goal = "Extract and structure all financial data from bank statement PDFs"
#   agent.backstory = "Expert at parsing financial documents..."

# Generated code (agents.py):
document_processor = Agent(
    role="Bank Statement Data Extractor",
    goal="Extract and structure all financial data from bank statement PDFs",
    backstory="Expert at parsing financial documents, handles both digital and scanned PDFs",
    tools=[pdf_parser_pymupdf, ocr_tesseract, json_transformer],
    verbose=True,
    allow_delegation=False
)
```

**Tool mapping:**
```python
# From spec:
#   tool.id = "pdf_parser_pymupdf"
#   tool.library_ref = "pdf_parser_pymupdf"
#   tool.config = {extract_tables: true}

# Generated code (tools.py):
# First: pull code_template from Tool Schema Library
# Then: wrap as CrewAI Tool
@tool
def pdf_parser_pymupdf(file_path: str) -> str:
    """Extracts text and tables from PDF files."""
    # [code_template content from Tool Schema Library]
    import fitz
    doc = fitz.open(file_path)
    # ... implementation from code_template ...
```

**Orchestration mapping:**
```python
# Sequential pattern:
crew = Crew(
    agents=[document_processor, financial_analyst, report_writer],
    tasks=[extract_task, analyze_task, report_task],
    process=Process.sequential,
    verbose=True
)

# Hierarchical pattern:
crew = Crew(
    agents=[manager, worker_1, worker_2],
    tasks=[manage_task, work_task_1, work_task_2],
    process=Process.hierarchical,
    manager_agent=manager,
    verbose=True
)
```

**Task generation (CrewAI-specific):**
```python
# Each agent gets a Task that defines its work
# Generated from spec.io_contracts
extract_task = Task(
    description="Extract text and transaction data from bank statement PDF at {input_path}",
    expected_output="JSON with transactions list, account_summary, and extraction_confidence",
    agent=document_processor
)
```

### LangGraph Compiler

Used when `spec.execution_flow.pattern` is `graph` or when conditional routing exists.

**State mapping:**
```python
# Generated from spec.io_contracts (union of all agent I/O fields)
class AgentState(TypedDict):
    # From document_processor output
    transactions: list[dict]
    account_summary: dict
    extraction_confidence: float
    # From financial_analyst output
    risk_score: float
    risk_factors: dict
    reasoning: str
    # From report_writer output
    report_markdown: str
    executive_summary: str
```

**Node mapping:**
```python
# Each agent becomes a node function
def document_processor_node(state: AgentState) -> AgentState:
    # Use tools: pdf_parser_pymupdf, ocr_tesseract, json_transformer
    # Read: state["bank_statement_path"]
    # Write: state["transactions"], state["account_summary"], state["extraction_confidence"]
    ...
    return {"transactions": result.transactions, ...}
```

**Edge mapping:**
```python
# From spec.execution_flow.graph.edges
graph = StateGraph(AgentState)
graph.add_node("document_processor", document_processor_node)
graph.add_node("financial_analyst", financial_analyst_node)
graph.add_node("report_writer", report_writer_node)

graph.add_edge("document_processor", "financial_analyst")
graph.add_edge("financial_analyst", "report_writer")
graph.add_edge("report_writer", END)

# Conditional edges from spec:
# graph.add_conditional_edges("validator", route_after_validation)
```

**Entry point mapping:**
```python
# main.py for LangGraph
from orchestration import graph

app = graph.compile()
result = app.invoke({
    "bank_statement_path": sys.argv[1] if len(sys.argv) > 1 else "input/statement.pdf"
})
print(json.dumps(result, indent=2))
```

## Tool Code Template Integration

The Builder does NOT generate tool implementations from scratch. It pulls `code_template` from each tool's ToolSchema in the library:

1. Look up `tool.library_ref` in Chroma `tool_schemas` collection
2. Pull the `code_template` field — this is tested, working Python code
3. Wrap the template in the framework's tool interface (CrewAI `@tool` decorator or plain function for LangGraph)
4. Apply `tool.config` values to parameterize the template

**If code_template is missing or empty:** Flag as validation error. The Builder cannot generate tool code from scratch — that's unreliable. The tool library must provide working templates.

## Config.yaml Generation

**Note on LLM model per generated agent:** The AgentSpec schema does not include a `model` field per agent — the Architect designs roles and tools, not LLM assignments. The Builder must decide which LLM each generated agent uses at compile time. Default strategy: use `gpt-4o-mini` for all generated agents (cheap, fast, sufficient for most tool-using agents). Override via config.yaml if the generated agent needs stronger reasoning.

```yaml
# Generated from spec metadata + tool configs
pipeline:
  name: loan_underwriting_copilot
  framework: crewai
  domain: loan_underwriting

default_model: gpt-4o-mini  # used unless overridden per agent

agents:
  document_processor:
    temperature: 0.1
  financial_analyst:
    model: gpt-4o         # override: needs stronger reasoning for risk assessment
    temperature: 0.0
  report_writer:
    temperature: 0.3

tools:
  pdf_parser_pymupdf:
    extract_tables: true
  ocr_tesseract:
    language: eng
    confidence_threshold: 0.6
```

## Requirements.txt Generation

Assembled from:
1. Framework dependency (`crewai` or `langgraph langchain-core`)
2. Each tool's `dependencies` field from ToolSchema
3. Common deps always included: `pydantic`, `python-dotenv`
4. Deduplicated, sorted, with version pins from tool schemas

```
# Generated requirements.txt
crewai>=0.41.0
langchain-core>=0.2.0
langchain-openai>=0.1.0
pydantic>=2.0.0
python-dotenv>=1.0.0
pymupdf>=1.23.0
pytesseract>=0.3.10
pandas>=2.0.0
```

## 3-Step Validation

Run before returning the CodeBundle. All three must pass.

### Step 1: Syntax Check
```python
import py_compile
for filename, content in code_bundle.files.items():
    if filename.endswith('.py'):
        # Write to temp file, compile
        py_compile.compile(temp_path, doraise=True)
```
Catches: syntax errors, unclosed brackets, invalid Python.

### Step 2: Import Check
```python
# Parse all import statements from generated code
# Verify each import is either:
#   - A stdlib module
#   - Listed in requirements.txt
#   - A local import (from agents import ..., from tools import ...)
```
Catches: missing dependencies, typos in package names, imports that won't resolve in the Docker container.

### Step 3: Schema Check
```python
# For each agent's node/task function:
#   - Parse function signature
#   - Compare input parameters against spec.io_contracts[agent].input_schema
#   - Compare return type/structure against spec.io_contracts[agent].output_schema
# Verify: every required field is consumed and produced
```
Catches: generated code doesn't match the contracts the Tester will validate against.

### Validation Failure Handling

If any step fails:
- Set `validation_passed = False`
- Populate `validation_errors` with specific error messages
- The Builder gets ONE self-retry: fix the errors and re-validate
- If self-retry also fails, output the CodeBundle with `validation_passed = False` — the Tester will catch it and route back

## Handling Test Failure Re-entry (Loop from Tester)

When the Builder receives a code-level failure from the Tester:

1. Read `state["failure_traces"]` — each trace has:
   - `error_type` (crash, wrong_output, missing_field, quality_fail)
   - `raw_error` (actual error message or bad output)
   - `failing_agent` (which agent in the generated pipeline)
   - `root_cause_analysis` (what went wrong)
   - `suggested_fix` (what to change)

2. Apply fixes to the specific files affected — don't regenerate the entire CodeBundle
3. Re-run 3-step validation
4. Increment `build_iteration`

**The Builder must NOT:**
- Change the AgentSpec (that's the Architect's job)
- Add tools that aren't in the spec
- Restructure the agent pipeline
- Modify io_contracts

**The Builder CAN:**
- Fix syntax errors in generated code
- Fix import statements
- Fix tool binding code
- Adjust how data flows between functions (implementation details)
- Fix config.yaml values

## Prompt Engineering Notes

**System prompt should establish:**
- Role: "You are a code compiler. You translate agent specifications into runnable Python code. You do NOT design systems — the spec tells you exactly what to build."
- Constraint: "Follow the spec exactly. Do not add features, change architecture, or 'improve' the design. Your job is faithful compilation."
- Quality: "Generated code must be production-quality Python: proper imports, type hints on function signatures, docstrings on public functions, clean formatting."
- Output: "Return a CodeBundle with all files as a dictionary of filename → content."
- Templates: "Tool implementations come from code_templates in the Tool Schema Library. Do not write tool code from scratch."

**Key behaviors to instruct:**
- Generate code that runs. Not pseudocode, not "fill in here," not TODO comments. Every line must be executable.
- Use the framework's documented API exactly — don't invent creative workarounds
- Config values go in config.yaml, not hardcoded in Python
- Error handling in generated code should match the spec's error_handling section for each agent
- requirements.txt must be complete — every import must resolve

## Example Output — PS-08 main.py

```python
"""Loan Underwriting Co-Pilot — Entry Point"""
import sys
import json
import yaml
from dotenv import load_dotenv

load_dotenv()

from orchestration import create_crew

def main():
    config_path = "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    input_path = sys.argv[1] if len(sys.argv) > 1 else "input/statement.pdf"

    crew = create_crew(config)
    result = crew.kickoff(inputs={"bank_statement_path": input_path})

    # Parse and output results
    output = {
        "risk_score": result.get("risk_score"),
        "executive_summary": result.get("executive_summary"),
        "report": result.get("report_markdown")
    }
    print(json.dumps(output, indent=2))

    # Write full report
    with open("output/risk_report.md", "w") as f:
        f.write(result.get("report_markdown", "No report generated"))

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Error Handling

| Error | Cause | Response |
|-------|-------|----------|
| Tool code_template missing | Tool Schema Library incomplete | Flag in validation_errors. Cannot proceed — tool implementations must come from the library. |
| Framework API mismatch | CrewAI or LangGraph API changed | Builder should use documented API patterns. If API errors occur at test time, it's a code-level fix. |
| Spec has inconsistent io_contracts | Critic missed something | Builder compiles faithfully. Tester will catch the runtime failure and trace it to spec. |
| Generated code too long for single LLM call | Complex spec with many agents | Split generation: generate agents.py, tools.py, orchestration.py separately, then assemble. |
| Self-retry fails validation again | Fundamental generation issue | Output with validation_passed=False. Tester routes back. If build_iteration hits max, Learner records failure. |
