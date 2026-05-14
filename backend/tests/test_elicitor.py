"""Tests for the Elicitor agent."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.agents.elicitor import (
    _compile_requirements,
    _generate_assumptions,
    _generate_questions,
    _query_domain_insights,
    _run_gap_analysis,
    elicitor_agent,
)
from app.models.requirements import (
    CategoryAssessment,
    GapAnalysisResult,
    QuestionCategory,
    RequirementsDoc,
)
from app.models.state import FrankensteinState


# ── Fixtures ─────────────────────────────────────────────────────────


def _make_gap_result(
    scores: dict[str, float], quality: str = "medium"
) -> GapAnalysisResult:
    """Helper to build a GapAnalysisResult from name→score dict."""
    cats = []
    for name, conf in scores.items():
        missing = ["field_a", "field_b"] if conf < 0.7 else []
        cats.append(
            CategoryAssessment(
                name=name,
                confidence=conf,
                addressed_fields=[],
                missing_fields=missing,
                notes="test",
            )
        )
    return GapAnalysisResult(categories=cats, overall_quality=quality)


def _make_requirements_json(**overrides) -> str:
    """Return a valid RequirementsDoc JSON string."""
    base = {
        "domain": "test domain",
        "inputs": [{"name": "input1", "format": "csv", "description": "test input", "example": "data.csv"}],
        "outputs": [{"name": "output1", "format": "json", "description": "test output", "example": "result.json"}],
        "process_steps": [
            {"step_number": 1, "description": "Process data", "rules": ["rule1"], "depends_on": []}
        ],
        "edge_cases": [{"description": "Missing input", "expected_handling": "Return error"}],
        "quality_criteria": [{"criterion": "Accuracy > 90%", "validation_method": "test suite"}],
        "constraints": ["Must complete in 60s"],
        "assumptions": [],
    }
    base.update(overrides)
    return json.dumps(base)


def _make_gap_json(scores: dict[str, float], quality: str = "medium") -> str:
    """Return gap analysis result as JSON string."""
    categories = []
    for name, conf in scores.items():
        missing = ["field_a", "field_b"] if conf < 0.7 else []
        addressed = ["field_c"] if conf >= 0.7 else []
        categories.append({
            "name": name,
            "confidence": conf,
            "addressed_fields": addressed,
            "missing_fields": missing,
            "notes": "test note",
        })
    return json.dumps({"categories": categories, "overall_quality": quality})


def _make_questions_json(categories: list[tuple[str, float, list[str]]]) -> str:
    """Return question generation result as JSON."""
    return json.dumps({
        "categories": [
            {"name": name, "confidence": conf, "questions": qs}
            for name, conf, qs in categories
        ]
    })


# ── Model tests ──────────────────────────────────────────────────────


class TestGapAnalysisResult:
    def test_gaps_returns_below_threshold(self):
        result = _make_gap_result({
            "Input/Output": 0.9,
            "Process": 0.3,
            "Data": 0.5,
            "Edge Cases": 0.8,
            "Quality Bar": 0.2,
        })
        gaps = result.gaps()
        assert len(gaps) == 3
        names = [g.name for g in gaps]
        assert "Process" in names
        assert "Data" in names
        assert "Quality Bar" in names
        assert "Input/Output" not in names

    def test_gaps_priority_order(self):
        result = _make_gap_result({
            "Input/Output": 0.4,
            "Process": 0.3,
            "Data": 0.5,
            "Edge Cases": 0.2,
            "Quality Bar": 0.1,
        })
        gaps = result.gaps()
        names = [g.name for g in gaps]
        assert names == ["Input/Output", "Process", "Data", "Edge Cases", "Quality Bar"]

    def test_all_complete_true(self):
        result = _make_gap_result({
            "Input/Output": 0.9,
            "Process": 0.8,
            "Data": 0.7,
            "Edge Cases": 0.75,
            "Quality Bar": 1.0,
        })
        assert result.all_complete() is True

    def test_all_complete_false(self):
        result = _make_gap_result({
            "Input/Output": 0.9,
            "Process": 0.69,
            "Data": 0.7,
            "Edge Cases": 0.75,
            "Quality Bar": 1.0,
        })
        assert result.all_complete() is False


# ── Helper function tests ────────────────────────────────────────────


class TestQueryDomainInsights:
    def test_empty_collection_returns_placeholder(self):
        chroma = MagicMock()
        chroma.find_domain_insights.return_value = []
        result = _query_domain_insights(chroma, "test prompt")
        assert "No domain insights" in result

    def test_with_results(self):
        chroma = MagicMock()
        chroma.find_domain_insights.return_value = [
            {"document": "Loan domain requires financial data"},
            {"document": "PDF parsing is common"},
        ]
        result = _query_domain_insights(chroma, "loan underwriting")
        assert "Loan domain" in result
        assert "PDF parsing" in result

    def test_exception_returns_placeholder(self):
        chroma = MagicMock()
        chroma.find_domain_insights.side_effect = Exception("connection failed")
        result = _query_domain_insights(chroma, "test")
        assert "No domain insights" in result


class TestRunGapAnalysis:
    def test_initial_analysis(self):
        llm = MagicMock()
        llm.call.return_value = _make_gap_json({
            "Input/Output": 0.8,
            "Process": 0.3,
            "Data": 0.5,
            "Edge Cases": 0.2,
            "Quality Bar": 0.4,
        })
        result = _run_gap_analysis(llm, "build me an agent", "no insights", [])
        assert isinstance(result, GapAnalysisResult)
        assert len(result.categories) == 5
        llm.call.assert_called_once()
        # Verify agent_name is "elicitor"
        assert llm.call.call_args.kwargs["agent_name"] == "elicitor"
        assert llm.call.call_args.kwargs["json_mode"] is True

    def test_rescoring_with_answers(self):
        llm = MagicMock()
        llm.call.return_value = _make_gap_json({
            "Input/Output": 0.9,
            "Process": 0.8,
            "Data": 0.7,
            "Edge Cases": 0.6,
            "Quality Bar": 0.5,
        })
        answers = [{"round": 1, "answers": "CSV input, JSON output", "timestamp": "2026-01-01T00:00:00Z"}]
        result = _run_gap_analysis(llm, "build me an agent", "no insights", answers)
        # Should include accumulated answers in user prompt
        call_args = llm.call.call_args
        assert "Re-analyze" in call_args.kwargs["user_prompt"]
        assert "Round 1" in call_args.kwargs["user_prompt"]


class TestGenerateQuestions:
    def test_returns_question_categories(self):
        llm = MagicMock()
        llm.call.return_value = _make_questions_json([
            ("Process", 0.3, ["What steps?", "Any decisions?"]),
            ("Data", 0.5, ["How much data?"]),
        ])
        gaps = [
            CategoryAssessment(name="Process", confidence=0.3, missing_fields=["main_task_description"], notes=""),
            CategoryAssessment(name="Data", confidence=0.5, missing_fields=["data_volume_estimate"], notes=""),
        ]
        result = _generate_questions(
            llm, "test", gaps, [], [], current_round=1, max_rounds=3, min_questions=1
        )
        assert len(result) == 2
        assert all(isinstance(c, QuestionCategory) for c in result)

    def test_priority_order_sorting(self):
        llm = MagicMock()
        # LLM returns in wrong order
        llm.call.return_value = _make_questions_json([
            ("Edge Cases", 0.2, ["What if it fails?"]),
            ("Input/Output", 0.4, ["What format?"]),
        ])
        gaps = [
            CategoryAssessment(name="Edge Cases", confidence=0.2, missing_fields=["known_failure_modes"], notes=""),
            CategoryAssessment(name="Input/Output", confidence=0.4, missing_fields=["input_format"], notes=""),
        ]
        result = _generate_questions(
            llm, "test", gaps, [], [], current_round=1, max_rounds=3, min_questions=1
        )
        assert result[0].name == "Input/Output"
        assert result[1].name == "Edge Cases"


class TestCompileRequirements:
    def test_returns_valid_requirements_doc(self):
        llm = MagicMock()
        llm.call.return_value = _make_requirements_json()
        result = _compile_requirements(
            llm, "build a loan agent", [], [], "no insights", max_rounds=3
        )
        assert isinstance(result, RequirementsDoc)
        assert result.domain == "test domain"
        assert len(result.inputs) > 0
        assert len(result.process_steps) > 0


class TestGenerateAssumptions:
    def test_returns_assumptions_list(self):
        llm = MagicMock()
        llm.call.return_value = json.dumps({
            "assumptions": [
                "Assuming single file input per run",
                "Assuming output goes to stdout",
            ]
        })
        result = _generate_assumptions(
            llm, "build agent", [], ["input_source", "output_destination"]
        )
        assert len(result) == 2
        assert "single file" in result[0]


# ── LLM routing tests ───────────────────────────────────────────────


class TestLLMRouting:
    def test_all_calls_use_elicitor_agent_name(self):
        """Every LLM call in the elicitor must use agent_name='elicitor'."""
        llm = MagicMock()
        llm.call.return_value = _make_gap_json({
            "Input/Output": 0.9, "Process": 0.9, "Data": 0.9,
            "Edge Cases": 0.9, "Quality Bar": 0.9,
        }, "high")

        _run_gap_analysis(llm, "test", "insights", [])
        assert llm.call.call_args.kwargs["agent_name"] == "elicitor"

    def test_json_mode_always_true(self):
        """All structured output calls use json_mode=True."""
        llm = MagicMock()
        llm.call.return_value = _make_gap_json({
            "Input/Output": 0.9, "Process": 0.9, "Data": 0.9,
            "Edge Cases": 0.9, "Quality Bar": 0.9,
        }, "high")

        _run_gap_analysis(llm, "test", "insights", [])
        assert llm.call.call_args.kwargs["json_mode"] is True


# ── Integration: elicitor_agent function ─────────────────────────────


class TestElicitorAgent:
    def test_high_quality_prompt_no_questions(self):
        """A comprehensive prompt should skip Q&A and go straight to compilation."""
        llm = MagicMock()
        chroma = MagicMock()
        chroma.find_domain_insights.return_value = []

        # First call: gap analysis — all categories complete
        gap_json = _make_gap_json({
            "Input/Output": 0.9, "Process": 0.85, "Data": 0.8,
            "Edge Cases": 0.75, "Quality Bar": 0.7,
        }, "high")

        # Second call: compilation
        req_json = _make_requirements_json()

        llm.call.side_effect = [gap_json, req_json]

        state: FrankensteinState = {
            "raw_prompt": "Build a loan underwriting agent that takes PDF bank statements, extracts financial data, calculates risk ratios, applies underwriting rules, and generates a risk assessment report in JSON format. Input is single PDF, output is JSON risk score 0-1. Must complete in 30 seconds. Handle missing pages gracefully.",
        }

        result = elicitor_agent(state, llm=llm, chroma=chroma)

        assert isinstance(result["requirements"], RequirementsDoc)
        assert result["requirements_approved"] is False
        assert result["elicitor_questions"] == []  # No questions needed
        assert result["human_answers"] == []

    def test_low_quality_prompt_triggers_questions(self):
        """A vague prompt should trigger gap analysis and question generation."""
        llm = MagicMock()
        chroma = MagicMock()
        chroma.find_domain_insights.return_value = []

        # Call 1: gap analysis — low quality
        gap_json_1 = _make_gap_json({
            "Input/Output": 0.3, "Process": 0.2, "Data": 0.1,
            "Edge Cases": 0.0, "Quality Bar": 0.0,
        }, "low")

        # Call 2: question generation
        questions_json = _make_questions_json([
            ("Input/Output", 0.3, ["What format?", "Where from?"]),
            ("Process", 0.2, ["What steps?", "Any decisions?"]),
        ])

        # We need to mock interrupt() since it pauses execution
        # For this test, simulate a single round where after answers all scores are high
        gap_json_2 = _make_gap_json({
            "Input/Output": 0.9, "Process": 0.85, "Data": 0.8,
            "Edge Cases": 0.75, "Quality Bar": 0.7,
        }, "high")

        # Call 3: answer extraction
        extract_json = json.dumps({
            "extracted_fields": {"input_format": "csv"},
            "coverage_notes": "good"
        })

        # Call 4: re-scoring (same as gap_json_2)
        # Call 5: compilation
        req_json = _make_requirements_json()

        llm.call.side_effect = [gap_json_1, questions_json, extract_json, gap_json_2, req_json]

        state: FrankensteinState = {"raw_prompt": "build agent"}

        with patch("app.agents.elicitor.interrupt", return_value="CSV input, JSON output, process data step by step"):
            result = elicitor_agent(state, llm=llm, chroma=chroma)

        assert len(result["elicitor_questions"]) == 1  # One round of questions
        assert result["elicitor_questions"][0]["round"] == 1
        assert len(result["human_answers"]) == 1
        assert isinstance(result["requirements"], RequirementsDoc)

    def test_max_rounds_flags_assumptions(self):
        """After MAX_ELICITOR_ROUNDS, remaining gaps become assumptions."""
        llm = MagicMock()
        chroma = MagicMock()
        chroma.find_domain_insights.return_value = []

        # Build 3 rounds of: gap analysis (gaps remain) → questions → extract → rescore
        # Then: assumption generation → compilation
        persistent_gap = _make_gap_json({
            "Input/Output": 0.9, "Process": 0.8, "Data": 0.7,
            "Edge Cases": 0.3, "Quality Bar": 0.4,
        }, "medium")

        questions = _make_questions_json([
            ("Edge Cases", 0.3, ["What if failure?"]),
            ("Quality Bar", 0.4, ["Success criteria?"]),
        ])

        extract = json.dumps({"extracted_fields": {}, "coverage_notes": "partial"})

        assumptions = json.dumps({"assumptions": ["Assume graceful degradation on error"]})
        req = _make_requirements_json(assumptions=["Assume graceful degradation on error"])

        # 3 rounds × (gap + questions + extract + rescore) + assumptions + compile
        # Round 1: gap, questions, extract, rescore
        # Round 2: questions, extract, rescore
        # Round 3: questions, extract, rescore
        # Then: assumptions, compile
        side_effects = [
            persistent_gap,    # initial gap analysis
            questions, extract, persistent_gap,  # round 1
            questions, extract, persistent_gap,  # round 2
            questions, extract, persistent_gap,  # round 3
            assumptions,       # assumption generation
            req,              # compilation
        ]
        llm.call.side_effect = side_effects

        state: FrankensteinState = {"raw_prompt": "build a complex agent system"}

        with patch("app.agents.elicitor.interrupt", return_value="some partial answer"):
            result = elicitor_agent(state, llm=llm, chroma=chroma)

        assert len(result["elicitor_questions"]) == 3  # 3 rounds
        assert len(result["human_answers"]) == 3
        assert "Assume graceful" in result["requirements"].assumptions[0]

    def test_chroma_empty_no_error(self):
        """Empty Chroma collection should not cause errors."""
        llm = MagicMock()
        chroma = MagicMock()
        chroma.find_domain_insights.return_value = []

        gap_json = _make_gap_json({
            "Input/Output": 0.9, "Process": 0.9, "Data": 0.9,
            "Edge Cases": 0.9, "Quality Bar": 0.9,
        }, "high")
        req_json = _make_requirements_json()
        llm.call.side_effect = [gap_json, req_json]

        state: FrankensteinState = {"raw_prompt": "comprehensive prompt here"}
        result = elicitor_agent(state, llm=llm, chroma=chroma)

        chroma.find_domain_insights.assert_called_once()
        assert isinstance(result["requirements"], RequirementsDoc)


# ── Pipeline graph tests ─────────────────────────────────────────────


class TestPipelineGraph:
    def test_graph_compiles(self):
        from app.pipeline.graph import compiled_graph
        assert compiled_graph is not None

    def test_graph_has_elicitor_node(self):
        from app.pipeline.graph import compiled_graph
        assert "elicitor" in compiled_graph.nodes

    def test_graph_has_checkpoint_node(self):
        from app.pipeline.graph import compiled_graph
        assert "human_review_requirements" in compiled_graph.nodes
