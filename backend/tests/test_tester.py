"""Tests for the Tester agent.

NOTE: Skipped pending rewrite for the new live-execution Tester architecture.
Old tests targeted internals (_check_syntax, _run_static_analysis) that have
been replaced by the shared `_validation` module + rule-based classifier.
"""

import pytest
pytest.skip("Tester rewritten — see _validation tests; legacy helpers removed", allow_module_level=True)

import json
from unittest.mock import MagicMock, PropertyMock, patch

from app.agents.tester import tester_agent as run_tester_agent
from app.models.code import CodeBundle
from app.models.spec import AgentSpec
from app.models.testing import FailureTrace, TestCase, TestReport
from app.services.docker_service import ExecutionResult


# ── Fixtures ─────────────────────────────────────────────────────────


VALID_SPEC_JSON = json.dumps({
    "metadata": {
        "name": "test_pipeline",
        "domain": "testing",
        "framework_target": "crewai",
        "decision_rationale": "Sequential flow.",
        "created_from_pattern": None,
    },
    "agents": [
        {
            "id": "worker",
            "role": "Worker",
            "goal": "Do work",
            "backstory": "A worker",
            "tools": [],
            "reasoning_strategy": "react",
            "receives_from": [],
            "sends_to": [],
        },
    ],
    "tools": [],
    "memory": {"strategy": "shared", "shared_keys": [], "persistence": "session"},
    "execution_flow": {"pattern": "sequential", "graph": None},
    "error_handling": [],
    "io_contracts": [
        {
            "agent_id": "worker",
            "input_schema": {"fields": [{"name": "input", "type": "string", "required": True}]},
            "output_schema": {"fields": [{"name": "output", "type": "string", "required": True}]},
        },
    ],
})


def _make_spec():
    return AgentSpec(**json.loads(VALID_SPEC_JSON))


def _make_code(files=None, valid=True):
    default_files = {"main.py": "print('hello')\n", "tools.py": "def t(): pass\n"}
    if not valid:
        default_files["broken.py"] = "def foo(\n"
    return CodeBundle(
        files=files or default_files,
        framework="crewai",
        validation_passed=valid,
        validation_errors=[] if valid else ["syntax error in broken.py"],
    )


def _mock_llm(return_value=None):
    llm = MagicMock()
    llm.call.return_value = return_value or json.dumps({
        "test_cases": [
            {
                "name": "test_basic",
                "description": "Basic test",
                "input_data": {"input": "hello"},
                "expected_output_schema": {},
                "quality_checks": ["output exists"],
                "timeout": 60,
            }
        ]
    })
    return llm


def _mock_docker(available=True, image_exists=True, exit_code=0, stdout="ok", stderr="", timed_out=False, error=""):
    docker = MagicMock()
    type(docker).available = PropertyMock(return_value=available)
    docker.image_exists.return_value = image_exists
    docker.run_code_bundle.return_value = ExecutionResult(
        exit_code=exit_code, stdout=stdout, stderr=stderr, timed_out=timed_out, error=error
    )
    return docker


# ── _generate_test_cases Tests ───────────────────────────────────────


class TestGenerateTestCases:
    def test_returns_test_case_list(self):
        llm = _mock_llm()
        result = _generate_test_cases(llm, _make_spec(), _make_code())
        assert len(result) == 1
        assert isinstance(result[0], TestCase)
        assert result[0].name == "test_basic"

    def test_parse_failure_returns_empty(self):
        llm = _mock_llm("not json")
        result = _generate_test_cases(llm, _make_spec(), _make_code())
        assert result == []


# ── _check_syntax Tests ──────────────────────────────────────────────


class TestCheckSyntax:
    def test_valid_files(self):
        code = _make_code({"main.py": "x = 1\n"})
        errors = _check_syntax(code)
        assert errors == []

    def test_invalid_files(self):
        code = _make_code({"bad.py": "def foo(\n"})
        errors = _check_syntax(code)
        assert len(errors) == 1
        assert errors[0]["file"] == "bad.py"

    def test_skips_non_py(self):
        code = _make_code({"readme.md": "not python at all def foo(\n"})
        errors = _check_syntax(code)
        assert errors == []


# ── _run_static_analysis Tests ───────────────────────────────────────


class TestRunStaticAnalysis:
    def test_returns_issues(self):
        llm = _mock_llm(json.dumps({
            "issues": [{"file": "main.py", "severity": "error", "description": "missing import"}]
        }))
        result = _run_static_analysis(llm, _make_spec(), _make_code())
        assert len(result) == 1
        assert result[0]["file"] == "main.py"

    def test_parse_failure_returns_empty(self):
        llm = _mock_llm("not json")
        result = _run_static_analysis(llm, _make_spec(), _make_code())
        assert result == []


# ── Docker Path Tests ────────────────────────────────────────────────


class TestDockerPaths:
    @patch("app.agents.tester._run_subprocess")
    def test_subprocess_fallback_when_unavailable(self, mock_sub):
        """When Docker unavailable, subprocess fallback runs instead."""
        mock_sub.return_value = ExecutionResult(
            exit_code=0, stdout="ok", stderr="", timed_out=False, error=""
        )
        llm = _mock_llm()
        llm.call.side_effect = [
            json.dumps({"test_cases": []}),
            json.dumps({"issues": []}),
        ]
        docker = _mock_docker(available=False)
        state = {"spec": _make_spec(), "generated_code": _make_code(), "build_iteration": 0}
        run_tester_agent(state, llm=llm, docker=docker)
        docker.run_code_bundle.assert_not_called()
        mock_sub.assert_called_once()

    @patch("app.agents.tester._run_subprocess")
    def test_subprocess_fallback_when_image_missing(self, mock_sub):
        """When Docker image missing, subprocess fallback runs."""
        mock_sub.return_value = ExecutionResult(
            exit_code=0, stdout="ok", stderr="", timed_out=False, error=""
        )
        llm = _mock_llm()
        llm.call.side_effect = [
            json.dumps({"test_cases": []}),
            json.dumps({"issues": []}),
        ]
        docker = _mock_docker(available=True, image_exists=False)
        state = {"spec": _make_spec(), "generated_code": _make_code(), "build_iteration": 0}
        run_tester_agent(state, llm=llm, docker=docker)
        docker.run_code_bundle.assert_not_called()
        mock_sub.assert_called_once()

    def test_calls_docker_when_available(self):
        llm = _mock_llm()
        llm.call.side_effect = [
            json.dumps({"test_cases": []}),
            json.dumps({"issues": []}),
        ]
        docker = _mock_docker(available=True, image_exists=True, exit_code=0)
        state = {"spec": _make_spec(), "generated_code": _make_code(), "build_iteration": 0}
        run_tester_agent(state, llm=llm, docker=docker)
        docker.run_code_bundle.assert_called_once()


# ── Docker Result Tests ──────────────────────────────────────────────


class TestDockerResults:
    def test_exit_code_0_passed(self):
        llm = _mock_llm()
        llm.call.side_effect = [
            json.dumps({"test_cases": []}),
            json.dumps({"issues": []}),
        ]
        docker = _mock_docker(exit_code=0)
        state = {"spec": _make_spec(), "generated_code": _make_code(), "build_iteration": 0}
        result = run_tester_agent(state, llm=llm, docker=docker)
        report = result["test_results"]
        docker_results = [r for r in report.results if r.test_name == "docker_execution"]
        assert len(docker_results) == 1
        assert docker_results[0].status == "passed"

    def test_exit_code_1_failed(self):
        llm = _mock_llm()
        llm.call.side_effect = [
            json.dumps({"test_cases": []}),
            json.dumps({"issues": []}),
            json.dumps({"failure_traces": []}),
        ]
        docker = _mock_docker(exit_code=1, stderr="runtime error")
        state = {"spec": _make_spec(), "generated_code": _make_code(), "build_iteration": 0}
        result = run_tester_agent(state, llm=llm, docker=docker)
        report = result["test_results"]
        docker_results = [r for r in report.results if r.test_name == "docker_execution"]
        assert docker_results[0].status == "failed"

    def test_timeout_failed(self):
        llm = _mock_llm()
        llm.call.side_effect = [
            json.dumps({"test_cases": []}),
            json.dumps({"issues": []}),
            json.dumps({"failure_traces": []}),
        ]
        docker = _mock_docker(timed_out=True, error="timed out")
        state = {"spec": _make_spec(), "generated_code": _make_code(), "build_iteration": 0}
        result = run_tester_agent(state, llm=llm, docker=docker)
        report = result["test_results"]
        docker_results = [r for r in report.results if r.test_name == "docker_execution"]
        assert docker_results[0].status == "failed"


# ── _trace_failures Tests ────────────────────────────────────────────


class TestTraceFailures:
    def test_generates_traces(self):
        llm = _mock_llm(json.dumps({
            "failure_traces": [{
                "test_name": "test_1",
                "error_type": "crash",
                "raw_error": "ImportError",
                "failing_agent": "worker",
                "root_cause_level": "code",
                "root_cause_analysis": "Missing import",
                "spec_decision_responsible": "tools",
                "suggested_fix": "Add import",
            }]
        }))
        result = _trace_failures(llm, _make_spec(), _make_code(), [{"error": "test"}])
        assert len(result) == 1
        assert isinstance(result[0], FailureTrace)

    def test_parse_failure_returns_fallback(self):
        llm = _mock_llm("not json")
        result = _trace_failures(llm, _make_spec(), _make_code(), [{"error": "test"}])
        assert len(result) == 1
        assert result[0].root_cause_level == "code"
        assert result[0].test_name == "parse_failure"


# ── tester_agent Tests ───────────────────────────────────────────────


class TestTesterAgent:
    @patch("app.agents.tester._run_subprocess")
    def test_all_passed_when_valid_code(self, mock_sub):
        mock_sub.return_value = ExecutionResult(
            exit_code=0, stdout="ok", stderr="", timed_out=False, error=""
        )
        llm = _mock_llm()
        llm.call.side_effect = [
            json.dumps({"test_cases": []}),
            json.dumps({"issues": []}),
        ]
        docker = _mock_docker(available=False)
        state = {"spec": _make_spec(), "generated_code": _make_code(), "build_iteration": 0}
        result = run_tester_agent(state, llm=llm, docker=docker)
        assert result["test_results"].all_passed is True

    @patch("app.agents.tester._run_subprocess")
    def test_increments_build_iteration(self, mock_sub):
        mock_sub.return_value = ExecutionResult(
            exit_code=0, stdout="ok", stderr="", timed_out=False, error=""
        )
        llm = _mock_llm()
        llm.call.side_effect = [
            json.dumps({"test_cases": []}),
            json.dumps({"issues": []}),
        ]
        docker = _mock_docker(available=False)
        state = {"spec": _make_spec(), "generated_code": _make_code(), "build_iteration": 2}
        result = run_tester_agent(state, llm=llm, docker=docker)
        assert result["build_iteration"] == 3

    @patch("app.agents.tester._run_subprocess")
    def test_returns_test_cases_and_results(self, mock_sub):
        mock_sub.return_value = ExecutionResult(
            exit_code=0, stdout="ok", stderr="", timed_out=False, error=""
        )
        llm = _mock_llm()
        llm.call.side_effect = [
            json.dumps({"test_cases": [{"name": "t1", "description": "d"}]}),
            json.dumps({"issues": []}),
        ]
        docker = _mock_docker(available=False)
        state = {"spec": _make_spec(), "generated_code": _make_code(), "build_iteration": 0}
        result = run_tester_agent(state, llm=llm, docker=docker)
        assert "test_cases" in result
        assert "test_results" in result
        assert "failure_traces" in result
        assert isinstance(result["test_results"], TestReport)
