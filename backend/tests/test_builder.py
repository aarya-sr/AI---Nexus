"""Tests for the Builder agent — code generation, validation, persistence."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.agents.builder import (
    CREWAI_SYSTEM,
    LANGGRAPH_SYSTEM,
    REBUILD_ADDENDUM,
    _collect_dependencies,
    _generate_code,
    _get_tool_templates,
    _persist_to_disk,
    _validate_syntax,
    builder_agent,
)
from app.models.code import CodeBundle
from app.models.spec import AgentSpec
from app.models.tools import ToolSchema


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
            "tools": ["tool_inst"],
            "reasoning_strategy": "react",
            "receives_from": [],
            "sends_to": [],
        },
    ],
    "tools": [
        {
            "id": "tool_inst",
            "library_ref": "test_tool",
            "config": {},
            "accepts": ["text"],
            "outputs": ["text"],
        }
    ],
    "memory": {"strategy": "shared", "shared_keys": ["data"], "persistence": "session"},
    "execution_flow": {"pattern": "sequential", "graph": None},
    "error_handling": [
        {"agent_id": "worker", "on_failure": "retry", "max_retries": 2, "fallback_agent": None},
    ],
    "io_contracts": [
        {
            "agent_id": "worker",
            "input_schema": {"fields": [{"name": "input", "type": "string", "required": True}]},
            "output_schema": {"fields": [{"name": "output", "type": "string", "required": True}]},
        },
    ],
})

VALID_CODE_FILES = {
    "main.py": "print('hello')\n",
    "agents.py": "def agent(): pass\n",
    "tools.py": "def tool(): pass\n",
    "requirements.txt": "crewai\n",
}


def _make_spec(framework="crewai"):
    data = json.loads(VALID_SPEC_JSON)
    data["metadata"]["framework_target"] = framework
    return AgentSpec(**data)


def _make_tool():
    return ToolSchema(
        id="test_tool",
        name="Test Tool",
        description="A test tool",
        category="testing",
        accepts=["text"],
        outputs=["text"],
        output_format="text",
        limitations=[],
        dependencies=["requests"],
        code_template="# template",
        compatible_with=[],
        incompatible_with=[],
    )


def _mock_llm(return_value=None):
    llm = MagicMock()
    llm.call.return_value = return_value or json.dumps(VALID_CODE_FILES)
    return llm


def _mock_chroma():
    chroma = MagicMock()
    chroma.get_tool_by_id.return_value = _make_tool()
    return chroma


# ── _generate_code Tests ─────────────────────────────────────────────


class TestGenerateCode:
    def test_crewai_system_prompt(self):
        llm = _mock_llm()
        spec = _make_spec("crewai")
        _generate_code(llm, spec, {}, None)
        kwargs = llm.call.call_args[1]
        assert "CrewAI" in kwargs["system_prompt"]

    def test_langgraph_system_prompt(self):
        llm = _mock_llm()
        spec = _make_spec("langgraph")
        _generate_code(llm, spec, {}, None)
        kwargs = llm.call.call_args[1]
        assert "LangGraph" in kwargs["system_prompt"]

    def test_rebuild_addendum_with_failure_feedback(self):
        llm = _mock_llm()
        spec = _make_spec()
        feedback = [{"test_name": "test_1", "error_type": "crash", "raw_error": "oops"}]
        _generate_code(llm, spec, {}, feedback)
        kwargs = llm.call.call_args[1]
        assert "PREVIOUS BUILD FAILED" in kwargs["system_prompt"]

    def test_no_rebuild_addendum_without_feedback(self):
        llm = _mock_llm()
        spec = _make_spec()
        _generate_code(llm, spec, {}, None)
        kwargs = llm.call.call_args[1]
        assert "PREVIOUS BUILD FAILED" not in kwargs["system_prompt"]

    def test_invalid_json_raises(self):
        llm = _mock_llm("not json at all")
        with pytest.raises(ValueError, match="invalid JSON"):
            _generate_code(llm, _make_spec(), {}, None)

    def test_non_dict_json_raises(self):
        llm = _mock_llm(json.dumps(["not", "a", "dict"]))
        with pytest.raises(ValueError, match="did not return"):
            _generate_code(llm, _make_spec(), {}, None)

    def test_filters_non_string_values(self):
        files_with_junk = {**VALID_CODE_FILES, "bad": 123, "also_bad": None}
        llm = _mock_llm(json.dumps(files_with_junk))
        result = _generate_code(llm, _make_spec(), {}, None)
        assert "bad" not in result
        assert "also_bad" not in result
        assert "main.py" in result


# ── _validate_syntax Tests ───────────────────────────────────────────


class TestValidateSyntax:
    def test_valid_python(self):
        files = {"main.py": "print('hello')\n"}
        passed, errors = _validate_syntax(files)
        assert passed is True
        assert errors == []

    def test_invalid_python(self):
        files = {"main.py": "def foo(\n"}
        passed, errors = _validate_syntax(files)
        assert passed is False
        assert len(errors) == 1
        assert "main.py" in errors[0]

    def test_skips_non_py_files(self):
        files = {"requirements.txt": "this is not python\ndef foo(\n"}
        passed, errors = _validate_syntax(files)
        assert passed is True
        assert errors == []


# ── _collect_dependencies Tests ──────────────────────────────────────


class TestCollectDependencies:
    def test_crewai_deps(self):
        spec = _make_spec("crewai")
        deps = _collect_dependencies(spec, {})
        assert "crewai" in deps

    def test_langgraph_deps(self):
        spec = _make_spec("langgraph")
        deps = _collect_dependencies(spec, {})
        assert "langgraph" in deps
        assert "langchain-core" in deps

    def test_merges_tool_deps(self):
        spec = _make_spec("crewai")
        templates = {"t1": {"dependencies": ["requests", "pandas"]}}
        deps = _collect_dependencies(spec, templates)
        assert "requests" in deps
        assert "pandas" in deps
        assert "crewai" in deps


# ── _get_tool_templates Tests ────────────────────────────────────────


class TestGetToolTemplates:
    def test_found_tool(self):
        chroma = _mock_chroma()
        spec = _make_spec()
        result = _get_tool_templates(chroma, spec)
        assert "test_tool" in result
        assert result["test_tool"]["code_template"] == "# template"

    def test_missing_tool_logs_warning(self, caplog):
        chroma = MagicMock()
        chroma.get_tool_by_id.return_value = None
        spec = _make_spec()
        import logging
        with caplog.at_level(logging.WARNING):
            result = _get_tool_templates(chroma, spec)
        assert result == {}
        assert "not found" in caplog.text


# ── builder_agent Tests ──────────────────────────────────────────────


class TestBuilderAgent:
    def test_returns_code_bundle(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = {"spec": _make_spec(), "session_id": ""}
        result = builder_agent(state, llm=llm, chroma=chroma)
        assert isinstance(result["generated_code"], CodeBundle)

    def test_validation_passed_true_for_valid_code(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = {"spec": _make_spec(), "session_id": ""}
        result = builder_agent(state, llm=llm, chroma=chroma)
        assert result["generated_code"].validation_passed is True

    def test_validation_passed_false_for_invalid_code(self):
        bad_files = {**VALID_CODE_FILES, "broken.py": "def foo(\n"}
        llm = _mock_llm(json.dumps(bad_files))
        chroma = _mock_chroma()
        state = {"spec": _make_spec(), "session_id": ""}
        result = builder_agent(state, llm=llm, chroma=chroma)
        assert result["generated_code"].validation_passed is False

    def test_di_pattern(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = {"spec": _make_spec(), "session_id": ""}
        builder_agent(state, llm=llm, chroma=chroma)
        kwargs = llm.call.call_args[1]
        assert kwargs["agent_name"] == "builder"
        assert kwargs["json_mode"] is True
        assert kwargs["temperature"] == 0.1


# ── _persist_to_disk Tests ───────────────────────────────────────────


class TestPersistToDisk:
    def test_writes_files(self, tmp_path):
        with patch("app.config.settings") as mock_settings:
            mock_settings.generated_agents_dir = str(tmp_path)
            _persist_to_disk("test-session", {"main.py": "print('hi')\n", "sub/helper.py": "x=1\n"})
            assert (tmp_path / "test-session" / "main.py").read_text() == "print('hi')\n"
            assert (tmp_path / "test-session" / "sub" / "helper.py").read_text() == "x=1\n"

    def test_builder_agent_skips_persist_when_no_session_id(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = {"spec": _make_spec()}
        with patch("app.agents.builder._persist_to_disk") as mock_persist:
            builder_agent(state, llm=llm, chroma=chroma)
            mock_persist.assert_not_called()

    def test_builder_agent_calls_persist_with_session_id(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = {"spec": _make_spec(), "session_id": "sess-123"}
        with patch("app.agents.builder._persist_to_disk") as mock_persist:
            builder_agent(state, llm=llm, chroma=chroma)
            mock_persist.assert_called_once()
            assert mock_persist.call_args[0][0] == "sess-123"
