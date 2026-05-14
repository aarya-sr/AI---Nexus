"""Tests for the Learner agent — outcome logic, pattern extraction, Chroma writes."""

import hashlib
import json
from unittest.mock import MagicMock, call, patch

import pytest

from app.agents.learner import (
    _extract_patterns,
    _store_learnings,
    learner_agent,
)
from app.models.learning import BuildOutcome
from app.models.requirements import RequirementsDoc
from app.models.spec import AgentSpec
from app.models.testing import TestReport, TestResult


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


def _make_requirements():
    return RequirementsDoc(
        domain="testing",
        inputs=[{"name": "input", "format": "text", "description": "Test input"}],
        outputs=[{"name": "output", "format": "json", "description": "Test output"}],
        process_steps=[
            {"step_number": 1, "description": "Process data", "rules": [], "depends_on": []},
        ],
        edge_cases=[],
        quality_criteria=[],
        constraints=[],
        assumptions=[],
    )


def _make_test_report(all_passed=True, passed=3, failed=0, total=3):
    results = []
    for i in range(passed):
        results.append(TestResult(test_name=f"test_pass_{i}", status="passed"))
    for i in range(failed):
        results.append(TestResult(test_name=f"test_fail_{i}", status="failed", stderr="err"))
    return TestReport(
        total=total, passed=passed, failed=failed, errors=0,
        all_passed=all_passed, results=results,
    )


def _mock_llm(patterns=None):
    llm = MagicMock()
    default_patterns = {
        "success_patterns": ["Good pattern"],
        "failure_patterns": ["Bad pattern"],
        "anti_patterns": ["Avoid this"],
        "lessons_learned": ["Learned this"],
    }
    llm.call.return_value = json.dumps(patterns or default_patterns)
    return llm


def _mock_chroma():
    chroma = MagicMock()
    return chroma


def _make_state(test_report=None, failure_traces=None):
    return {
        "spec": _make_spec(),
        "requirements": _make_requirements(),
        "test_results": test_report or _make_test_report(),
        "failure_traces": failure_traces or [],
        "spec_iteration": 1,
        "build_iteration": 1,
    }


# ── Outcome Logic Tests ──────────────────────────────────────────────


class TestOutcomeLogic:
    def test_all_passed_success(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = _make_state(test_report=_make_test_report(all_passed=True))
        result = learner_agent(state, llm=llm, chroma=chroma)
        assert result["build_outcome"].outcome == "success"

    def test_some_passed_partial_success(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        report = _make_test_report(all_passed=False, passed=2, failed=1, total=3)
        state = _make_state(test_report=report)
        result = learner_agent(state, llm=llm, chroma=chroma)
        assert result["build_outcome"].outcome == "partial_success"

    def test_none_passed_failure(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        report = _make_test_report(all_passed=False, passed=0, failed=3, total=3)
        state = _make_state(test_report=report)
        result = learner_agent(state, llm=llm, chroma=chroma)
        assert result["build_outcome"].outcome == "failure"

    def test_no_results_failure(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = _make_state()
        state["test_results"] = None
        result = learner_agent(state, llm=llm, chroma=chroma)
        assert result["build_outcome"].outcome == "failure"


# ── Pattern Extraction Tests ─────────────────────────────────────────


class TestPatternExtraction:
    def test_returns_four_lists(self):
        llm = _mock_llm()
        state = _make_state()
        result = _extract_patterns(llm, state)
        assert "success_patterns" in result
        assert "failure_patterns" in result
        assert "anti_patterns" in result
        assert "lessons_learned" in result

    def test_parse_failure_returns_empty(self):
        llm = MagicMock()
        llm.call.return_value = "not json"
        state = _make_state()
        result = _extract_patterns(llm, state)
        assert result["success_patterns"] == []
        assert result["anti_patterns"] == []


# ── Chroma Storage Tests ─────────────────────────────────────────────


class TestChromaWrites:
    def test_store_spec_pattern_called(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = _make_state()
        learner_agent(state, llm=llm, chroma=chroma)
        chroma.store_spec_pattern.assert_called_once()

    def test_store_anti_pattern_per_anti_pattern(self):
        llm = _mock_llm({"success_patterns": [], "failure_patterns": [],
                         "anti_patterns": ["ap1", "ap2"], "lessons_learned": []})
        chroma = _mock_chroma()
        state = _make_state()
        learner_agent(state, llm=llm, chroma=chroma)
        assert chroma.store_anti_pattern.call_count == 2

    def test_store_domain_insight_per_lesson(self):
        llm = _mock_llm({"success_patterns": [], "failure_patterns": [],
                         "anti_patterns": [], "lessons_learned": ["l1", "l2", "l3"]})
        chroma = _mock_chroma()
        state = _make_state()
        learner_agent(state, llm=llm, chroma=chroma)
        assert chroma.store_domain_insight.call_count == 3

    def test_update_tool_compatibility_on_success(self):
        llm = _mock_llm({"success_patterns": [], "failure_patterns": [],
                         "anti_patterns": [], "lessons_learned": []})
        chroma = _mock_chroma()
        # Need tools in spec for compatibility check
        spec_data = json.loads(VALID_SPEC_JSON)
        spec_data["tools"] = [
            {"id": "t1", "library_ref": "tool_a", "config": {}, "accepts": [], "outputs": []},
            {"id": "t2", "library_ref": "tool_b", "config": {}, "accepts": [], "outputs": []},
        ]
        spec = AgentSpec(**spec_data)
        state = _make_state(test_report=_make_test_report(all_passed=True))
        state["spec"] = spec
        learner_agent(state, llm=llm, chroma=chroma)
        assert chroma.update_tool_compatibility.call_count >= 1

    def test_empty_patterns_no_anti_pattern_writes(self):
        llm = _mock_llm({"success_patterns": [], "failure_patterns": [],
                         "anti_patterns": [], "lessons_learned": []})
        chroma = _mock_chroma()
        state = _make_state()
        learner_agent(state, llm=llm, chroma=chroma)
        chroma.store_anti_pattern.assert_not_called()
        chroma.store_domain_insight.assert_not_called()


# ── Requirements Hash Tests ──────────────────────────────────────────


class TestRequirementsHash:
    def test_hash_consistency(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = _make_state()
        result1 = learner_agent(state, llm=llm, chroma=chroma)
        result2 = learner_agent(state, llm=llm, chroma=chroma)
        assert result1["build_outcome"].requirements_hash == result2["build_outcome"].requirements_hash


# ── Return Value Tests ───────────────────────────────────────────────


class TestLearnerReturn:
    def test_returns_build_outcome(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = _make_state()
        result = learner_agent(state, llm=llm, chroma=chroma)
        assert "build_outcome" in result
        assert isinstance(result["build_outcome"], BuildOutcome)
