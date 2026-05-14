"""Tester agent — validates generated code and traces failures.

Model: gpt-4o-mini
Purpose: Generate test cases from spec contracts, validate code, trace
         failures back to spec-level or code-level root causes.
Process: Generate tests → static validation → Docker execution → failure tracing.

Docker execution runs the generated code in a sandboxed container when Docker
is available. Falls back to static-only validation when Docker is unavailable.
"""

import json
import logging
import py_compile
import tempfile
from pathlib import Path

from app.models.code import CodeBundle
from app.models.spec import AgentSpec
from app.models.state import FrankensteinState
from app.models.testing import FailureTrace, TestCase, TestReport, TestResult
from app.services.docker_service import DockerService, ExecutionResult
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

AGENT_NAME = "tester"

# ── System Prompts ────────────────────────────────────────────────────

TEST_GENERATION_SYSTEM = """\
You are the Tester agent generating test cases for an AI agent pipeline.

Given the AgentSpec (with io_contracts) and generated code, produce test cases
that would verify correctness if the code were executed.

For each test case:
- name: descriptive snake_case (e.g. "test_bank_statement_parsing")
- description: what the test verifies
- input_data: synthetic test input matching the pipeline's entry point schema
- expected_output_schema: JSON schema the output must conform to
- quality_checks: human-readable assertions (e.g. "risk_score between 0 and 1")
- timeout: seconds (default 60)

Focus on:
1. Happy path — standard input → expected output shape
2. Required fields — every output_schema required field is present
3. Edge cases from requirements — if any were specified
4. Contract compliance — output types match declared schemas

Return JSON: {"test_cases": [...]}"""

FAILURE_ANALYSIS_SYSTEM = """\
You are the Tester agent analysing failures in generated code.

Given:
1. AgentSpec
2. Generated code files
3. Validation errors found

For each failure, determine:

- test_name: which check failed
- error_type: crash | wrong_output | missing_field | quality_fail
- raw_error: the actual error message
- failing_agent: which agent in the generated pipeline is responsible
- root_cause_level:
    "code"  — implementation bug (syntax, logic, wrong function signature)
              → loops back to Builder
    "spec"  — design flaw (wrong tool, missing agent, schema mismatch)
              → loops back to Architect
- root_cause_analysis: 1-2 sentence explanation
- spec_decision_responsible: which spec field/decision caused the issue
- suggested_fix: specific, actionable fix

Return JSON: {"failure_traces": [...]}"""

STATIC_ANALYSIS_SYSTEM = """\
You are analysing generated code for an AI agent pipeline.

Check the code files against the spec for these issues:
1. Missing imports — are all used modules imported?
2. Function signature mismatches — do agent functions accept/return the right types?
3. Tool wiring — is every tool used by its assigned agent?
4. Contract compliance — does each agent's return dict match its output_schema?
5. Entry point — does main.py actually invoke the pipeline correctly?

For each issue found, report:
{
  "file": "filename.py",
  "line_hint": "near which function/class",
  "severity": "error" | "warning",
  "description": "what is wrong",
  "fix": "how to fix it"
}

Return JSON: {"issues": [...]}"""


# ── Agent Entry Point ─────────────────────────────────────────────────


def tester_agent(
    state: FrankensteinState,
    *,
    llm: LLMService | None = None,
    docker: DockerService | None = None,
) -> dict:
    """Tester node — validates generated code, traces failures."""
    from app.services.llm_service import LLMService as _LS

    if llm is None:
        llm = _LS()
    if docker is None:
        docker = DockerService()

    spec: AgentSpec = state["spec"]
    code: CodeBundle = state["generated_code"]
    logger.info("Tester: validating '%s' (%d files)", spec.metadata.name, len(code.files))

    # ── 1. Generate test cases ───────────────────────────────────────
    test_cases = _generate_test_cases(llm, spec, code)
    logger.info("Tester: generated %d test cases", len(test_cases))

    # ── 2. Static validation ─────────────────────────────────────────
    syntax_errors = _check_syntax(code)
    analysis_issues = _run_static_analysis(llm, spec, code)
    all_errors = syntax_errors + analysis_issues

    # ── 3. Docker execution (when available) ─────────────────────────
    exec_result: ExecutionResult | None = None
    if docker.available and docker.image_exists() and not syntax_errors:
        logger.info("Tester: running code in Docker sandbox")
        exec_result = docker.run_code_bundle(code)
        if exec_result.timed_out:
            logger.warning("Tester: Docker execution timed out")
        elif exec_result.exit_code != 0:
            logger.warning("Tester: Docker execution failed (exit %d)", exec_result.exit_code)
        else:
            logger.info("Tester: Docker execution succeeded")
    elif syntax_errors:
        logger.info("Tester: skipping Docker — syntax errors found")
    elif not docker.available:
        logger.info("Tester: Docker not available — static-only validation")
    elif not docker.image_exists():
        logger.info("Tester: runner image not built — static-only validation")

    # ── 4. Build test report ─────────────────────────────────────────
    results: list[TestResult] = []

    # Syntax results
    failed_files: set[str] = set()
    for err in syntax_errors:
        failed_files.add(err["file"])
        results.append(
            TestResult(
                test_name=f"syntax_{err['file']}",
                status="failed",
                stderr=err["error"],
                validation_details=f"Syntax error in {err['file']}",
            )
        )

    # Static analysis results
    for issue in analysis_issues:
        status = "failed" if issue["severity"] == "error" else "passed"
        results.append(
            TestResult(
                test_name=f"analysis_{issue['file']}_{issue.get('line_hint', 'unknown')}",
                status=status,
                stderr=issue.get("description", ""),
                validation_details=issue.get("fix", ""),
            )
        )

    # Docker execution results
    if exec_result is not None:
        if exec_result.timed_out:
            results.append(
                TestResult(
                    test_name="docker_execution",
                    status="failed",
                    stderr=exec_result.error,
                    stdout=exec_result.stdout,
                    validation_details=f"Execution timed out: {exec_result.error}",
                )
            )
            all_errors.append({
                "file": code.entry_point,
                "severity": "error",
                "error": exec_result.error,
                "description": "Docker execution timed out",
                "fix": "Check for infinite loops or long-running operations",
            })
        elif exec_result.exit_code != 0:
            results.append(
                TestResult(
                    test_name="docker_execution",
                    status="failed",
                    stderr=exec_result.stderr,
                    stdout=exec_result.stdout,
                    validation_details=f"Exit code {exec_result.exit_code}: {exec_result.stderr[:500]}",
                )
            )
            all_errors.append({
                "file": code.entry_point,
                "severity": "error",
                "error": exec_result.stderr[:500],
                "description": f"Runtime error (exit {exec_result.exit_code})",
                "fix": "Fix the runtime error in the generated code",
            })
        elif exec_result.error:
            results.append(
                TestResult(
                    test_name="docker_execution",
                    status="error",
                    stderr=exec_result.error,
                    stdout=exec_result.stdout,
                    validation_details=f"Docker error: {exec_result.error}",
                )
            )
        else:
            results.append(
                TestResult(
                    test_name="docker_execution",
                    status="passed",
                    stdout=exec_result.stdout,
                    validation_details="Code executed successfully in sandbox",
                )
            )

    # Passing results for clean .py files
    for fname in code.files:
        if fname.endswith(".py") and fname not in failed_files:
            results.append(
                TestResult(test_name=f"syntax_{fname}", status="passed")
            )

    # Validation-passed check (from builder)
    if not code.validation_passed and code.validation_errors:
        for ve in code.validation_errors:
            results.append(
                TestResult(
                    test_name="builder_validation",
                    status="failed",
                    stderr=ve,
                    validation_details="Builder's own validation flagged this",
                )
            )

    n_failed = sum(1 for r in results if r.status == "failed")
    n_errors = sum(1 for r in results if r.status == "error")
    all_passed = n_failed == 0 and n_errors == 0

    report = TestReport(
        total=len(results),
        passed=sum(1 for r in results if r.status == "passed"),
        failed=n_failed,
        errors=n_errors,
        all_passed=all_passed,
        results=results,
    )

    # ── 5. Failure tracing ───────────────────────────────────────────
    failure_traces: list[FailureTrace] = []
    if not all_passed:
        failure_traces = _trace_failures(llm, spec, code, all_errors)
        logger.info("Tester: %d failure traces generated", len(failure_traces))
    else:
        logger.info("Tester: all checks passed")

    return {
        "test_cases": test_cases,
        "test_results": report,
        "failure_traces": failure_traces,
        "build_iteration": state.get("build_iteration", 0) + 1,
    }


# ── Test Case Generation ─────────────────────────────────────────────


def _generate_test_cases(
    llm: LLMService, spec: AgentSpec, code: CodeBundle
) -> list[TestCase]:
    """LLM generates test cases from spec contracts."""
    # Only send a summary of code files (names + first lines) to save tokens
    code_summary = {}
    for fname, content in code.files.items():
        lines = content.split("\n")
        code_summary[fname] = "\n".join(lines[:30]) + (
            "\n... (truncated)" if len(lines) > 30 else ""
        )

    user_msg = (
        f"## AgentSpec\n\n{spec.model_dump_json(indent=2)}"
        f"\n\n## Generated Code (summary)\n\n{json.dumps(code_summary, indent=2)}"
    )

    response = llm.call(
        agent_name=AGENT_NAME,
        system_prompt=TEST_GENERATION_SYSTEM,
        user_prompt=user_msg,
        json_mode=True,
        temperature=0.2,
    )

    try:
        data = json.loads(response)
        return [TestCase(**tc) for tc in data.get("test_cases", [])]
    except (json.JSONDecodeError, Exception) as e:
        logger.error("Tester: test generation parse failed: %s", e)
        return []


# ── Syntax Checking ──────────────────────────────────────────────────


def _check_syntax(code: CodeBundle) -> list[dict]:
    """py_compile every .py file."""
    errors: list[dict] = []
    for fname, content in code.files.items():
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
            errors.append(
                {
                    "file": fname,
                    "severity": "error",
                    "error": str(e),
                    "description": f"Syntax error in {fname}",
                    "fix": "Fix the syntax error",
                }
            )
        finally:
            if tmp:
                tmp.unlink(missing_ok=True)
    return errors


# ── Static Analysis (LLM) ────────────────────────────────────────────


def _run_static_analysis(
    llm: LLMService, spec: AgentSpec, code: CodeBundle
) -> list[dict]:
    """LLM checks code against spec for structural issues."""
    user_msg = (
        f"## AgentSpec\n\n{spec.model_dump_json(indent=2)}"
        f"\n\n## Generated Code\n\n{json.dumps(code.files, indent=2)}"
    )

    response = llm.call(
        agent_name=AGENT_NAME,
        system_prompt=STATIC_ANALYSIS_SYSTEM,
        user_prompt=user_msg,
        json_mode=True,
        temperature=0.1,
    )

    try:
        data = json.loads(response)
        return data.get("issues", [])
    except (json.JSONDecodeError, Exception) as e:
        logger.error("Tester: static analysis parse failed: %s", e)
        return []


# ── Failure Tracing ──────────────────────────────────────────────────


def _trace_failures(
    llm: LLMService,
    spec: AgentSpec,
    code: CodeBundle,
    errors: list[dict],
) -> list[FailureTrace]:
    """Map failures back to spec decisions (code-level vs spec-level)."""
    user_msg = (
        f"## AgentSpec\n\n{spec.model_dump_json(indent=2)}"
        f"\n\n## Generated Code\n\n{json.dumps(code.files, indent=2)}"
        f"\n\n## Validation Errors\n\n{json.dumps(errors, indent=2)}"
    )

    response = llm.call(
        agent_name=AGENT_NAME,
        system_prompt=FAILURE_ANALYSIS_SYSTEM,
        user_prompt=user_msg,
        json_mode=True,
        temperature=0.1,
    )

    try:
        data = json.loads(response)
        return [FailureTrace(**ft) for ft in data.get("failure_traces", [])]
    except (json.JSONDecodeError, Exception) as e:
        logger.error("Tester: failure trace parse failed: %s", e)
        # Return a generic trace so the pipeline can still route
        return [
            FailureTrace(
                test_name="parse_failure",
                error_type="crash",
                raw_error=str(e),
                failing_agent="unknown",
                root_cause_level="code",
                root_cause_analysis="Failure trace generation itself failed",
                spec_decision_responsible="N/A",
                suggested_fix="Regenerate code with stricter output format",
            )
        ]
