"""Tests for the Critic agent — 6 attack vectors and feedback loop routing."""

import json
from unittest.mock import MagicMock

import pytest

from app.agents.critic import (
    critic_agent,
    _check_circular_dependencies,
    _check_format_compatibility,
    _check_dependency_completeness,
    _check_dead_ends,
    _check_resource_conflicts,
    _transitive_deps,
)
from app.models.critique import CritiqueReport, Finding
from app.models.spec import (
    AgentDef,
    AgentSpec,
    ErrorHandler,
    ExecutionFlow,
    GraphDef,
    GraphEdge,
    IOContract,
    IOSchema,
    MemoryConfig,
    SchemaField,
    SpecMetadata,
    ToolRef,
)
from app.pipeline.graph import route_after_critique


# ── Fixtures ─────────────────────────────────────────────────────────


def _make_spec(
    agents=None,
    edges=None,
    error_handling=None,
    io_contracts=None,
    shared_keys=None,
    pattern="sequential",
):
    """Build an AgentSpec with sensible defaults, overridable per test."""
    if agents is None:
        agents = [
            AgentDef(id="a", role="Agent A", goal="Do A", backstory="A"),
            AgentDef(id="b", role="Agent B", goal="Do B", backstory="B"),
        ]

    graph = None
    if edges is not None:
        nodes = list({e.from_agent for e in edges} | {e.to_agent for e in edges})
        graph = GraphDef(nodes=nodes, edges=edges)
        pattern = "graph"

    return AgentSpec(
        metadata=SpecMetadata(
            name="test_pipeline",
            domain="test",
            framework_target="crewai",
        ),
        agents=agents,
        tools=[],
        memory=MemoryConfig(
            strategy="shared" if shared_keys else "none",
            shared_keys=shared_keys or [],
        ),
        execution_flow=ExecutionFlow(pattern=pattern, graph=graph),
        error_handling=error_handling or [],
        io_contracts=io_contracts or [],
    )


# ── Vector 1: Circular Dependencies ─────────────────────────────────


class TestCircularDependencies:
    def test_no_edges_no_findings(self):
        spec = _make_spec()
        assert _check_circular_dependencies(spec) == []

    def test_linear_chain_no_cycle(self):
        edges = [
            GraphEdge(from_agent="a", to_agent="b"),
            GraphEdge(from_agent="b", to_agent="c"),
        ]
        agents = [
            AgentDef(id="a", role="A", goal="A", backstory="A"),
            AgentDef(id="b", role="B", goal="B", backstory="B"),
            AgentDef(id="c", role="C", goal="C", backstory="C"),
        ]
        spec = _make_spec(agents=agents, edges=edges)
        assert _check_circular_dependencies(spec) == []

    def test_cycle_detected_as_critical(self):
        edges = [
            GraphEdge(from_agent="a", to_agent="b"),
            GraphEdge(from_agent="b", to_agent="a"),
        ]
        spec = _make_spec(edges=edges)
        findings = _check_circular_dependencies(spec)
        assert len(findings) == 1
        assert findings[0].severity == "critical"
        assert findings[0].vector == "circular_dependencies"

    def test_three_node_cycle(self):
        edges = [
            GraphEdge(from_agent="a", to_agent="b"),
            GraphEdge(from_agent="b", to_agent="c"),
            GraphEdge(from_agent="c", to_agent="a"),
        ]
        agents = [
            AgentDef(id="a", role="A", goal="A", backstory="A"),
            AgentDef(id="b", role="B", goal="B", backstory="B"),
            AgentDef(id="c", role="C", goal="C", backstory="C"),
        ]
        spec = _make_spec(agents=agents, edges=edges)
        findings = _check_circular_dependencies(spec)
        assert len(findings) == 1
        assert findings[0].severity == "critical"


# ── Vector 2: Format Compatibility ──────────────────────────────────


class TestFormatCompatibility:
    def test_matching_schemas_no_findings(self):
        edges = [GraphEdge(from_agent="a", to_agent="b")]
        contracts = [
            IOContract(
                agent_id="a",
                output_schema=IOSchema(fields=[SchemaField(name="data", type="string")]),
            ),
            IOContract(
                agent_id="b",
                input_schema=IOSchema(fields=[SchemaField(name="data", type="string")]),
            ),
        ]
        spec = _make_spec(edges=edges, io_contracts=contracts)
        findings = _check_format_compatibility(spec)
        assert len(findings) == 0

    def test_missing_field_is_critical(self):
        edges = [GraphEdge(from_agent="a", to_agent="b")]
        contracts = [
            IOContract(
                agent_id="a",
                output_schema=IOSchema(fields=[SchemaField(name="data", type="string")]),
            ),
            IOContract(
                agent_id="b",
                input_schema=IOSchema(fields=[SchemaField(name="missing_field", type="string")]),
            ),
        ]
        spec = _make_spec(edges=edges, io_contracts=contracts)
        findings = _check_format_compatibility(spec)
        assert any(f.severity == "critical" and "missing_field" in f.description for f in findings)

    def test_type_mismatch_is_warning(self):
        edges = [GraphEdge(from_agent="a", to_agent="b")]
        contracts = [
            IOContract(
                agent_id="a",
                output_schema=IOSchema(fields=[SchemaField(name="score", type="string")]),
            ),
            IOContract(
                agent_id="b",
                input_schema=IOSchema(fields=[SchemaField(name="score", type="float")]),
            ),
        ]
        spec = _make_spec(edges=edges, io_contracts=contracts)
        findings = _check_format_compatibility(spec)
        assert any(f.severity == "warning" and "Type mismatch" in f.description for f in findings)

    def test_missing_contract_is_warning(self):
        edges = [GraphEdge(from_agent="a", to_agent="b")]
        # No contracts at all
        spec = _make_spec(edges=edges, io_contracts=[])
        findings = _check_format_compatibility(spec)
        assert any(f.severity == "warning" and "No I/O contract" in f.description for f in findings)

    def test_optional_field_not_flagged(self):
        edges = [GraphEdge(from_agent="a", to_agent="b")]
        contracts = [
            IOContract(
                agent_id="a",
                output_schema=IOSchema(fields=[]),
            ),
            IOContract(
                agent_id="b",
                input_schema=IOSchema(
                    fields=[SchemaField(name="optional_data", type="string", required=False)]
                ),
            ),
        ]
        spec = _make_spec(edges=edges, io_contracts=contracts)
        findings = _check_format_compatibility(spec)
        assert not any("optional_data" in f.description for f in findings)


# ── Vector 3: Dependency Completeness ────────────────────────────────


class TestDependencyCompleteness:
    def test_satisfied_dependencies_no_findings(self):
        edges = [GraphEdge(from_agent="a", to_agent="b")]
        contracts = [
            IOContract(
                agent_id="a",
                output_schema=IOSchema(fields=[SchemaField(name="data", type="string")]),
            ),
            IOContract(
                agent_id="b",
                input_schema=IOSchema(fields=[SchemaField(name="data", type="string")]),
            ),
        ]
        spec = _make_spec(edges=edges, io_contracts=contracts)
        findings = _check_dependency_completeness(spec)
        assert len(findings) == 0

    def test_unsatisfied_dependency_is_critical(self):
        edges = [GraphEdge(from_agent="a", to_agent="b")]
        contracts = [
            IOContract(
                agent_id="a",
                output_schema=IOSchema(fields=[]),
            ),
            IOContract(
                agent_id="b",
                input_schema=IOSchema(fields=[SchemaField(name="needed", type="string")]),
            ),
        ]
        spec = _make_spec(edges=edges, io_contracts=contracts)
        findings = _check_dependency_completeness(spec)
        assert any(f.severity == "critical" and "needed" in f.description for f in findings)

    def test_entry_point_agent_skipped(self):
        """Entry agents (no upstream) should not be checked."""
        edges = [GraphEdge(from_agent="a", to_agent="b")]
        contracts = [
            IOContract(
                agent_id="a",
                input_schema=IOSchema(fields=[SchemaField(name="external", type="string")]),
            ),
        ]
        spec = _make_spec(edges=edges, io_contracts=contracts)
        findings = _check_dependency_completeness(spec)
        # 'a' is entry point, should not flag 'external' as missing
        assert not any("external" in f.description for f in findings)


# ── Vector 4: Dead-End Analysis ──────────────────────────────────────


class TestDeadEnds:
    def test_missing_error_handling_is_warning(self):
        spec = _make_spec(error_handling=[])
        findings = _check_dead_ends(spec)
        assert len(findings) == 2  # one per agent
        assert all(f.severity == "warning" for f in findings)

    def test_all_agents_handled_no_findings(self):
        eh = [
            ErrorHandler(agent_id="a"),
            ErrorHandler(agent_id="b"),
        ]
        spec = _make_spec(error_handling=eh)
        findings = _check_dead_ends(spec)
        assert len(findings) == 0

    def test_skip_with_dependents_is_critical(self):
        edges = [GraphEdge(from_agent="a", to_agent="b")]
        eh = [
            ErrorHandler(agent_id="a", on_failure="skip"),
            ErrorHandler(agent_id="b"),
        ]
        spec = _make_spec(edges=edges, error_handling=eh)
        findings = _check_dead_ends(spec)
        assert any(
            f.severity == "critical" and "skip" in f.description
            for f in findings
        )

    def test_skip_without_dependents_ok(self):
        edges = [GraphEdge(from_agent="a", to_agent="b")]
        eh = [
            ErrorHandler(agent_id="a"),
            ErrorHandler(agent_id="b", on_failure="skip"),  # b has no dependents
        ]
        spec = _make_spec(edges=edges, error_handling=eh)
        findings = _check_dead_ends(spec)
        assert not any(f.severity == "critical" for f in findings)


# ── Vector 5: Resource Conflicts ─────────────────────────────────────


class TestResourceConflicts:
    def test_no_shared_keys_no_findings(self):
        spec = _make_spec(shared_keys=[])
        assert _check_resource_conflicts(spec) == []

    def test_parallel_with_shared_keys_warns(self):
        spec = _make_spec(shared_keys=["state"], pattern="parallel")
        findings = _check_resource_conflicts(spec)
        assert any(f.severity == "warning" and "race condition" in f.description for f in findings)

    def test_sequential_with_shared_keys_ok(self):
        edges = [GraphEdge(from_agent="a", to_agent="b")]
        spec = _make_spec(edges=edges, shared_keys=["state"])
        findings = _check_resource_conflicts(spec)
        # a→b is sequential, no parallel conflict
        assert len(findings) == 0

    def test_parallel_agents_in_graph_flagged(self):
        """Two agents with no dependency between them + shared keys."""
        agents = [
            AgentDef(id="a", role="A", goal="A", backstory="A"),
            AgentDef(id="b", role="B", goal="B", backstory="B"),
            AgentDef(id="c", role="C", goal="C", backstory="C"),
        ]
        # a→c and b→c, but a and b are parallel
        edges = [
            GraphEdge(from_agent="a", to_agent="c"),
            GraphEdge(from_agent="b", to_agent="c"),
        ]
        spec = _make_spec(agents=agents, edges=edges, shared_keys=["buffer"])
        findings = _check_resource_conflicts(spec)
        assert any("a" in f.description and "b" in f.description for f in findings)


# ── Transitive Dependencies Helper ──────────────────────────────────


class TestTransitiveDeps:
    def test_empty_deps(self):
        assert _transitive_deps("a", {}) == set()

    def test_direct_dep(self):
        deps = {"b": {"a"}}
        assert _transitive_deps("b", deps) == {"a"}

    def test_transitive_chain(self):
        deps = {"c": {"b"}, "b": {"a"}}
        assert _transitive_deps("c", deps) == {"a", "b"}


# ── Feedback Loop Routing ────────────────────────────────────────────


class TestRouteAfterCritique:
    def test_no_critique_routes_to_checkpoint(self):
        state = {}
        assert route_after_critique(state) == "human_review_spec"

    def test_no_criticals_routes_to_checkpoint(self):
        critique = CritiqueReport(
            findings=[
                Finding(
                    vector="test", severity="warning", description="minor",
                    location="x", evidence="y", suggested_fix="z",
                )
            ],
            summary="OK",
            iteration=1,
        )
        state = {"critique": critique, "spec_iteration": 1}
        assert route_after_critique(state) == "human_review_spec"

    def test_criticals_route_back_to_architect(self):
        critique = CritiqueReport(
            findings=[
                Finding(
                    vector="format_compatibility", severity="critical",
                    description="Missing field", location="x",
                    evidence="y", suggested_fix="z",
                )
            ],
            summary="Issues found",
            iteration=1,
        )
        state = {"critique": critique, "spec_iteration": 1}
        assert route_after_critique(state) == "architect"

    def test_max_iterations_stops_loop(self):
        critique = CritiqueReport(
            findings=[
                Finding(
                    vector="format_compatibility", severity="critical",
                    description="Still broken", location="x",
                    evidence="y", suggested_fix="z",
                )
            ],
            summary="Still issues",
            iteration=3,
        )
        from app.config import settings
        state = {"critique": critique, "spec_iteration": settings.max_spec_iterations}
        assert route_after_critique(state) == "human_review_spec"


# ── LLM Routing Tests ───────────────────────────────────────────────


class TestCriticLLMRouting:
    def test_critic_uses_correct_agent_name(self):
        llm = MagicMock()
        llm.call.return_value = json.dumps({
            "additional_findings": [],
            "summary": "Looks good",
        })
        spec = _make_spec()
        state = {"spec": spec, "spec_iteration": 1}

        critic_agent(state, llm=llm)

        call_kwargs = llm.call.call_args[1]
        assert call_kwargs["agent_name"] == "critic"

    def test_critic_uses_json_mode(self):
        llm = MagicMock()
        llm.call.return_value = json.dumps({
            "additional_findings": [],
            "summary": "Clean",
        })
        spec = _make_spec()
        state = {"spec": spec, "spec_iteration": 1}

        critic_agent(state, llm=llm)

        call_kwargs = llm.call.call_args[1]
        assert call_kwargs["json_mode"] is True


# ── Integration Tests ────────────────────────────────────────────────


class TestCriticIntegration:
    def test_critic_returns_critique_report(self):
        llm = MagicMock()
        llm.call.return_value = json.dumps({
            "additional_findings": [
                {
                    "vector": "tool_validation",
                    "severity": "warning",
                    "description": "Tool X seems wrong",
                    "location": "agent.extractor",
                    "evidence": "Category mismatch",
                    "suggested_fix": "Use tool Y",
                }
            ],
            "summary": "Minor issues found",
        })

        spec = _make_spec(
            error_handling=[ErrorHandler(agent_id="a"), ErrorHandler(agent_id="b")]
        )
        state = {"spec": spec, "spec_iteration": 1}

        result = critic_agent(state, llm=llm)

        assert "critique" in result
        assert isinstance(result["critique"], CritiqueReport)
        assert len(result["critique"].findings) >= 1
        assert result["critique"].summary == "Minor issues found"

    def test_critic_handles_llm_parse_failure(self):
        llm = MagicMock()
        llm.call.return_value = "not valid json!!!"

        spec = _make_spec(
            error_handling=[ErrorHandler(agent_id="a"), ErrorHandler(agent_id="b")]
        )
        state = {"spec": spec, "spec_iteration": 1}

        result = critic_agent(state, llm=llm)

        # Should still return a report with programmatic findings
        assert isinstance(result["critique"], CritiqueReport)
        assert "parse failed" in result["critique"].summary.lower()
