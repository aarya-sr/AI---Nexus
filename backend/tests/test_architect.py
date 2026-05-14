"""Tests for the Architect agent — RAG queries, task decomposition, spec compilation."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.agents.architect import (
    architect_agent,
    _generate,
    _requirements_summary,
    _format_tools,
    _parse_spec,
    _revise,
)
from app.models.requirements import RequirementsDoc
from app.models.spec import AgentSpec
from app.models.tools import ToolSchema


# ── Fixtures ─────────────────────────────────────────────────────────


def _make_requirements():
    return RequirementsDoc(
        domain="loan-underwriting",
        inputs=[
            {"name": "application_pdf", "format": "pdf", "description": "Loan application document"}
        ],
        outputs=[
            {"name": "risk_report", "format": "json", "description": "Risk assessment report"}
        ],
        process_steps=[
            {"step_number": 1, "description": "Extract text from PDF", "rules": [], "depends_on": []},
            {"step_number": 2, "description": "Analyze financial data", "rules": [], "depends_on": [1]},
            {"step_number": 3, "description": "Generate risk score", "rules": [], "depends_on": [2]},
        ],
        edge_cases=[{"description": "Corrupted PDF", "expected_handling": "Return error with reason"}],
        quality_criteria=[{"criterion": "Accuracy > 90%", "validation_method": "Manual review sample"}],
        constraints=["Must complete in under 30 seconds"],
        assumptions=[],
    )


def _make_tool():
    return ToolSchema(
        id="pdf_parser",
        name="PDF Parser",
        description="Extracts text from PDF documents",
        category="text_extraction",
        accepts=["pdf"],
        outputs=["text"],
        output_format="text",
        limitations=["Max 50 pages"],
        dependencies=["pypdf"],
        code_template="# pdf parser template",
        compatible_with=["text_analyzer"],
        incompatible_with=[],
    )


VALID_SPEC_JSON = json.dumps({
    "metadata": {
        "name": "loan_underwriting_pipeline",
        "domain": "loan-underwriting",
        "framework_target": "sequential",
        "decision_rationale": "Sequential flow suits linear processing chain.",
        "created_from_pattern": None,
    },
    "agents": [
        {
            "id": "extractor",
            "role": "PDF Text Extractor",
            "goal": "Extract text from loan application PDFs",
            "backstory": "Expert at OCR and text extraction",
            "tools": ["pdf_parser_inst"],
            "reasoning_strategy": "react",
            "receives_from": [],
            "sends_to": ["analyzer"],
        },
        {
            "id": "analyzer",
            "role": "Financial Analyzer",
            "goal": "Analyze financial data from extracted text",
            "backstory": "Domain expert in financial analysis",
            "tools": [],
            "reasoning_strategy": "cot",
            "receives_from": ["extractor"],
            "sends_to": [],
        },
    ],
    "tools": [
        {
            "id": "pdf_parser_inst",
            "library_ref": "pdf_parser",
            "config": {},
            "accepts": ["pdf"],
            "outputs": ["text"],
        }
    ],
    "memory": {"strategy": "shared", "shared_keys": ["extracted_text"], "persistence": "session"},
    "execution_flow": {"pattern": "sequential", "graph": None},
    "error_handling": [
        {"agent_id": "extractor", "on_failure": "retry", "max_retries": 2, "fallback_agent": None},
        {"agent_id": "analyzer", "on_failure": "retry", "max_retries": 2, "fallback_agent": None},
    ],
    "io_contracts": [
        {
            "agent_id": "extractor",
            "input_schema": {"fields": [{"name": "pdf_path", "type": "string", "required": True}]},
            "output_schema": {"fields": [{"name": "extracted_text", "type": "string", "required": True}]},
        },
        {
            "agent_id": "analyzer",
            "input_schema": {"fields": [{"name": "extracted_text", "type": "string", "required": True}]},
            "output_schema": {"fields": [{"name": "risk_score", "type": "float", "required": True}]},
        },
    ],
})


def _mock_llm():
    llm = MagicMock()
    llm.call.return_value = VALID_SPEC_JSON
    return llm


def _mock_chroma():
    chroma = MagicMock()
    chroma.find_similar_specs.return_value = []
    chroma.check_anti_patterns.return_value = []
    chroma.find_tools_for_capability.return_value = [_make_tool()]
    return chroma


# ── RAG Query Tests (Story 2.1) ─────────────────────────────────────


class TestArchitectRAG:
    """Tests for RAG queries and tool matching."""

    def test_generate_queries_chroma_for_similar_specs(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = {"requirements": _make_requirements(), "spec_iteration": 0}

        _generate(state, llm, chroma)

        chroma.find_similar_specs.assert_called_once()
        args = chroma.find_similar_specs.call_args
        assert "loan-underwriting" in args[0][0]

    def test_generate_queries_anti_patterns(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = {"requirements": _make_requirements(), "spec_iteration": 0}

        _generate(state, llm, chroma)

        chroma.check_anti_patterns.assert_called_once()

    def test_generate_queries_tools_per_process_step(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        reqs = _make_requirements()
        state = {"requirements": reqs, "spec_iteration": 0}

        _generate(state, llm, chroma)

        # Should query once per process step
        assert chroma.find_tools_for_capability.call_count == len(reqs.process_steps)

    def test_generate_deduplicates_tools(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        # Return same tool for all queries
        tool = _make_tool()
        chroma.find_tools_for_capability.return_value = [tool]

        state = {"requirements": _make_requirements(), "spec_iteration": 0}
        result = _generate(state, llm, chroma)

        # tool_library_matches should have only 1 entry despite 3 process steps
        assert len(result["tool_library_matches"]) == 1

    def test_generate_handles_empty_rag_results(self):
        """First build — no past specs, no anti-patterns, works from scratch."""
        llm = _mock_llm()
        chroma = _mock_chroma()
        chroma.find_similar_specs.return_value = []
        chroma.check_anti_patterns.return_value = []
        chroma.find_tools_for_capability.return_value = []

        state = {"requirements": _make_requirements(), "spec_iteration": 0}
        result = _generate(state, llm, chroma)

        assert result["spec"] is not None
        assert result["tool_library_matches"] == []

    def test_generate_includes_past_specs_in_prompt(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        chroma.find_similar_specs.return_value = [{"id": "past-1", "document": "old spec"}]

        state = {"requirements": _make_requirements(), "spec_iteration": 0}
        _generate(state, llm, chroma)

        # Check that LLM prompt includes past specs
        call_kwargs = llm.call.call_args[1]
        assert "Past Similar Specs" in call_kwargs["user_prompt"]

    def test_generate_includes_anti_patterns_in_prompt(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        chroma.check_anti_patterns.return_value = [{"id": "ap-1", "document": "bad pattern"}]

        state = {"requirements": _make_requirements(), "spec_iteration": 0}
        _generate(state, llm, chroma)

        call_kwargs = llm.call.call_args[1]
        assert "Anti-Patterns" in call_kwargs["user_prompt"]


# ── Task Decomposition & Tool Matching Tests ─────────────────────────


class TestTaskDecomposition:
    """Tests for helper functions around task decomposition."""

    def test_requirements_summary_includes_domain(self):
        reqs = _make_requirements()
        summary = _requirements_summary(reqs)
        assert "loan-underwriting" in summary

    def test_requirements_summary_includes_inputs(self):
        reqs = _make_requirements()
        summary = _requirements_summary(reqs)
        assert "application_pdf" in summary

    def test_requirements_summary_includes_process_steps(self):
        reqs = _make_requirements()
        summary = _requirements_summary(reqs)
        assert "Extract text from PDF" in summary

    def test_format_tools_omits_code_template(self):
        tools = [_make_tool()]
        formatted = _format_tools(tools)
        parsed = json.loads(formatted)
        assert "code_template" not in parsed[0]

    def test_format_tools_includes_key_fields(self):
        tools = [_make_tool()]
        formatted = _format_tools(tools)
        parsed = json.loads(formatted)
        assert parsed[0]["id"] == "pdf_parser"
        assert parsed[0]["accepts"] == ["pdf"]
        assert parsed[0]["compatible_with"] == ["text_analyzer"]


# ── Spec Compilation Tests (Story 2.2) ───────────────────────────────


class TestSpecCompilation:
    """Tests for spec parsing and compilation."""

    def test_parse_valid_spec(self):
        spec = _parse_spec(VALID_SPEC_JSON)
        assert isinstance(spec, AgentSpec)
        assert spec.metadata.name == "loan_underwriting_pipeline"
        assert spec.metadata.domain == "loan-underwriting"

    def test_parse_spec_agents(self):
        spec = _parse_spec(VALID_SPEC_JSON)
        assert len(spec.agents) == 2
        assert spec.agents[0].id == "extractor"
        assert spec.agents[1].id == "analyzer"

    def test_parse_spec_tools(self):
        spec = _parse_spec(VALID_SPEC_JSON)
        assert len(spec.tools) == 1
        assert spec.tools[0].library_ref == "pdf_parser"

    def test_parse_spec_normalizes_edge_keys(self):
        """LLMs sometimes output 'from'/'to' instead of 'from_agent'/'to_agent'."""
        data = json.loads(VALID_SPEC_JSON)
        data["execution_flow"] = {
            "pattern": "graph",
            "graph": {
                "nodes": ["a", "b"],
                "edges": [{"from": "a", "to": "b"}],
            },
        }
        spec = _parse_spec(json.dumps(data))
        assert spec.execution_flow.graph.edges[0].from_agent == "a"
        assert spec.execution_flow.graph.edges[0].to_agent == "b"

    def test_parse_spec_invalid_json_raises(self):
        with pytest.raises(ValueError, match="invalid JSON"):
            _parse_spec("not json at all")

    def test_parse_spec_invalid_schema_raises(self):
        with pytest.raises(ValueError, match="invalid spec"):
            _parse_spec('{"bad": "data"}')

    def test_generate_returns_spec_and_reasoning(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = {"requirements": _make_requirements(), "spec_iteration": 0}

        result = _generate(state, llm, chroma)

        assert isinstance(result["spec"], AgentSpec)
        assert isinstance(result["architect_reasoning"], str)
        assert result["spec_iteration"] == 1

    def test_generate_increments_spec_iteration(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = {"requirements": _make_requirements(), "spec_iteration": 2}

        result = _generate(state, llm, chroma)
        assert result["spec_iteration"] == 3


# ── LLM Routing Tests ────────────────────────────────────────────────


class TestArchitectLLMRouting:
    """Tests that architect uses correct agent_name and settings."""

    def test_generate_routes_to_architect_agent_name(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = {"requirements": _make_requirements(), "spec_iteration": 0}

        _generate(state, llm, chroma)

        call_kwargs = llm.call.call_args[1]
        assert call_kwargs["agent_name"] == "architect"

    def test_generate_uses_json_mode(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = {"requirements": _make_requirements(), "spec_iteration": 0}

        _generate(state, llm, chroma)

        call_kwargs = llm.call.call_args[1]
        assert call_kwargs["json_mode"] is True

    def test_generate_uses_low_temperature(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = {"requirements": _make_requirements(), "spec_iteration": 0}

        _generate(state, llm, chroma)

        call_kwargs = llm.call.call_args[1]
        assert call_kwargs["temperature"] == 0.15


# ── Revision Mode Tests ──────────────────────────────────────────────


class TestArchitectRevision:
    """Tests for the revision mode (post-critique loop)."""

    def test_revise_called_when_critique_present(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        spec = _parse_spec(VALID_SPEC_JSON)

        from app.models.critique import CritiqueReport, Finding

        critique = CritiqueReport(
            findings=[
                Finding(
                    vector="format_compatibility",
                    severity="critical",
                    description="Type mismatch",
                    location="edge extractor→analyzer",
                    evidence="string vs int",
                    suggested_fix="Align types",
                )
            ],
            summary="Needs fixing",
            iteration=1,
        )

        state = {
            "requirements": _make_requirements(),
            "spec": spec,
            "critique": critique,
            "spec_iteration": 1,
        }

        result = architect_agent(state, llm=llm, chroma=chroma)
        assert isinstance(result["spec"], AgentSpec)
        assert result["spec_iteration"] == 2

    def test_revise_uses_revision_prompt(self):
        llm = _mock_llm()
        spec = _parse_spec(VALID_SPEC_JSON)

        from app.models.critique import CritiqueReport

        critique = CritiqueReport(findings=[], summary="OK", iteration=1)

        state = {
            "requirements": _make_requirements(),
            "spec": spec,
            "critique": critique,
            "spec_iteration": 1,
        }

        _revise(state, llm)

        call_kwargs = llm.call.call_args[1]
        assert "revising" in call_kwargs["system_prompt"].lower()
        assert call_kwargs["temperature"] == 0.1

    def test_generate_mode_when_no_critique(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = {"requirements": _make_requirements(), "spec_iteration": 0}

        # No critique in state → generate mode
        result = architect_agent(state, llm=llm, chroma=chroma)
        assert isinstance(result["spec"], AgentSpec)


# ── Integration Test ─────────────────────────────────────────────────


class TestArchitectIntegration:
    """Integration test for the full architect_agent function."""

    def test_full_generate_flow(self):
        llm = _mock_llm()
        chroma = _mock_chroma()
        state = {
            "requirements": _make_requirements(),
            "spec_iteration": 0,
        }

        result = architect_agent(state, llm=llm, chroma=chroma)

        assert "spec" in result
        assert "architect_reasoning" in result
        assert "tool_library_matches" in result
        assert "past_spec_matches" in result
        assert "spec_iteration" in result
        assert isinstance(result["spec"], AgentSpec)
        assert result["spec_iteration"] == 1
