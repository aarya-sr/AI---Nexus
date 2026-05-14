"""Builder agent — compiles validated specs into working code.

Model: claude-sonnet-4-6
Purpose: Template-aware code generation for CrewAI or LangGraph projects.
Process: Read spec + tool code_templates → select framework compiler →
         generate project files → validate syntax → package as CodeBundle.

Handles rebuild: when failure_traces are present, incorporates fix feedback.
"""

import json
import logging
import py_compile
import tempfile
from pathlib import Path

from app.models.code import CodeBundle
from app.models.spec import AgentSpec
from app.models.state import FrankensteinState
from app.models.tools import ToolSchema
from app.services.chroma_service import ChromaService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

AGENT_NAME = "builder"

# ── Framework-specific system prompts ─────────────────────────────────

_SHARED_RULES = """\

## CRITICAL RULES
- Every tool in spec.tools MUST be implemented in tools.py using code_templates
- Every agent in spec.agents MUST appear in the orchestration
- Tool implementations come from code_templates — adapt, do NOT rewrite
- requirements.txt MUST list all dependencies (from spec.tools + framework)
- All generated Python files MUST be syntactically valid
- Use exact agent IDs, roles, goals, backstories from the spec

Return a single JSON object mapping filename → complete source code:
{"main.py": "...", "agents.py": "...", ...}
"""

CREWAI_SYSTEM = """\
You are the Builder agent generating a **CrewAI** project from an AgentSpec.

Produce a complete, runnable Python project as JSON: {filename: source_code}.

## Required Files

### main.py
```python
from orchestration import create_crew

def main():
    crew = create_crew()
    result = crew.kickoff(inputs={})
    import json
    print(json.dumps({"result": result.raw}, indent=2))

if __name__ == "__main__":
    main()
```

### agents.py
```python
from crewai import Agent
from tools import *

def create_agents() -> dict[str, Agent]:
    return {
        "agent_id": Agent(
            role="from spec",
            goal="from spec",
            backstory="from spec",
            tools=[tool_function_name],
            verbose=True,
        ),
    }
```

### tools.py
Each tool wraps a code_template with the @tool decorator:
```python
from crewai.tools import tool

@tool("Tool Display Name")
def tool_function(param: str) -> str:
    \"\"\"Description from tool schema.\"\"\"
    # code_template implementation adapted here
    ...
```

### orchestration.py
```python
from crewai import Crew, Task, Process
from agents import create_agents

def create_crew() -> Crew:
    agents = create_agents()
    tasks = [
        Task(description="...", agent=agents["id"], expected_output="..."),
    ]
    return Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
    )
```

### config.yaml
Agent configuration in YAML format.

### requirements.txt
crewai plus all tool dependencies.
""" + _SHARED_RULES

LANGGRAPH_SYSTEM = """\
You are the Builder agent generating a **LangGraph** project from an AgentSpec.

Produce a complete, runnable Python project as JSON: {filename: source_code}.

## Required Files

### main.py
```python
from orchestration import create_graph

def main():
    graph = create_graph()
    result = graph.invoke({})
    import json
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    main()
```

### state.py
```python
from typing import TypedDict

class PipelineState(TypedDict, total=False):
    # Union of all io_contract fields
    field_name: type
```

### agents.py
Each agent is a function: state → partial update dict.
```python
from tools import *

def agent_id(state: dict) -> dict:
    data = state["input_field"]
    result = tool_function(data)
    return {"output_field": result}
```

### tools.py
Tool implementations from code_templates (plain functions, no decorator):
```python
def tool_function(input_param: type) -> type:
    # code_template implementation
    ...
```

### orchestration.py
```python
from langgraph.graph import StateGraph, END
from state import PipelineState
from agents import *

def create_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("agent_id", agent_id)
    graph.set_entry_point("first_agent")
    graph.add_edge("agent_a", "agent_b")
    # conditional edges if spec has conditions
    graph.add_edge("last_agent", END)
    return graph.compile()
```

### requirements.txt
langgraph, langchain-core, plus all tool dependencies.
""" + _SHARED_RULES

REBUILD_ADDENDUM = """\

## PREVIOUS BUILD FAILED — FIX THESE ISSUES

The following failures were traced from the last build attempt.
Address each one in the regenerated code.  Do NOT introduce new issues.

Failure traces:
{failure_traces}
"""


# ── Agent Entry Point ─────────────────────────────────────────────────


def builder_agent(
    state: FrankensteinState,
    *,
    llm: LLMService | None = None,
    chroma: ChromaService | None = None,
) -> dict:
    """Builder node — compiles AgentSpec into a CodeBundle."""
    from app.services.chroma_service import ChromaService as _CS
    from app.services.llm_service import LLMService as _LS

    if llm is None:
        llm = _LS()
    if chroma is None:
        chroma = _CS()

    spec: AgentSpec = state["spec"]
    logger.info(
        "Builder: compiling '%s' → %s",
        spec.metadata.name,
        spec.metadata.framework_target,
    )

    # ── Gather tool code_templates ────────────────────────────────────
    tool_templates = _get_tool_templates(chroma, spec)
    logger.info("Builder: loaded %d tool templates", len(tool_templates))

    # ── Failure feedback from previous iteration ─────────────────────
    failure_feedback = None
    if state.get("failure_traces"):
        failure_feedback = [ft.model_dump() for ft in state["failure_traces"]]

    # ── Generate code ────────────────────────────────────────────────
    files = _generate_code(llm, spec, tool_templates, failure_feedback)

    # ── Validate syntax ──────────────────────────────────────────────
    passed, errors = _validate_syntax(files)
    if errors:
        logger.warning("Builder: %d validation errors: %s", len(errors), errors)
    else:
        logger.info("Builder: all files pass syntax check")

    # ── Collect dependencies ─────────────────────────────────────────
    deps = _collect_dependencies(spec, tool_templates)

    return {
        "generated_code": CodeBundle(
            files=files,
            framework=spec.metadata.framework_target,
            dependencies=deps,
            validation_passed=passed,
            validation_errors=errors,
        ),
    }


# ── Code Generation ──────────────────────────────────────────────────


def _generate_code(
    llm: LLMService,
    spec: AgentSpec,
    tool_templates: dict[str, dict],
    failure_feedback: list[dict] | None,
) -> dict[str, str]:
    """Single LLM call to produce all project files."""
    if spec.metadata.framework_target == "crewai":
        system = CREWAI_SYSTEM
    else:
        system = LANGGRAPH_SYSTEM

    if failure_feedback:
        system += REBUILD_ADDENDUM.format(
            failure_traces=json.dumps(failure_feedback, indent=2)
        )

    user_parts = [
        "## AgentSpec\n\n" + spec.model_dump_json(indent=2),
        "\n\n## Tool Code Templates\n\n" + json.dumps(tool_templates, indent=2),
    ]

    response = llm.call(
        agent_name=AGENT_NAME,
        system_prompt=system,
        user_prompt="\n".join(user_parts),
        json_mode=True,
        temperature=0.1,
    )

    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        logger.error("Builder: invalid JSON from LLM: %s", e)
        raise ValueError(f"Builder returned invalid JSON: {e}") from e

    if not isinstance(data, dict):
        raise ValueError("Builder did not return a filename→code mapping")

    return {k: v for k, v in data.items() if isinstance(v, str)}


# ── Tool Template Retrieval ──────────────────────────────────────────


def _get_tool_templates(
    chroma: ChromaService, spec: AgentSpec
) -> dict[str, dict]:
    """Look up code_templates for every tool referenced in the spec."""
    templates: dict[str, dict] = {}
    for tool_ref in spec.tools:
        tool: ToolSchema | None = chroma.get_tool_by_id(tool_ref.library_ref)
        if tool:
            templates[tool_ref.library_ref] = {
                "id": tool.id,
                "name": tool.name,
                "description": tool.description,
                "code_template": tool.code_template,
                "dependencies": tool.dependencies,
                "accepts": tool.accepts,
                "outputs": tool.outputs,
            }
        else:
            logger.warning(
                "Builder: tool '%s' not found in library", tool_ref.library_ref
            )
    return templates


# ── Validation ────────────────────────────────────────────────────────


def _validate_syntax(files: dict[str, str]) -> tuple[bool, list[str]]:
    """py_compile every .py file; return (all_passed, error_list)."""
    errors: list[str] = []
    for fname, content in files.items():
        if not fname.endswith(".py"):
            continue
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".py", mode="w", delete=False
            ) as f:
                f.write(content)
                f.flush()
                tmp = Path(f.name)
            py_compile.compile(str(tmp), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"{fname}: {e}")
        finally:
            if tmp:
                tmp.unlink(missing_ok=True)
    return len(errors) == 0, errors


# ── Dependency Collection ─────────────────────────────────────────────


def _collect_dependencies(
    spec: AgentSpec, tool_templates: dict[str, dict]
) -> list[str]:
    """Merge framework deps + tool deps into one list."""
    deps: set[str] = set()

    if spec.metadata.framework_target == "crewai":
        deps.add("crewai")
    else:
        deps.update(["langgraph", "langchain-core"])

    for tmpl in tool_templates.values():
        for d in tmpl.get("dependencies", []):
            deps.add(d)

    return sorted(deps)
