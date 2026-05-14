"""Tests for the requirements checkpoint node and approve endpoint."""

import pytest
from unittest.mock import MagicMock, patch

from app.pipeline.checkpoints import human_checkpoint_requirements
from app.models.requirements import RequirementsDoc


# ── Fixtures ─────────────────────────────────────────────────────────


def _make_requirements():
    return RequirementsDoc(
        domain="test-domain",
        inputs=[{"name": "input1", "format": "json", "description": "test input"}],
        outputs=[{"name": "output1", "format": "json", "description": "test output"}],
        process_steps=[
            {"step_number": 1, "description": "do thing", "rules": [], "depends_on": []}
        ],
        edge_cases=[],
        quality_criteria=[],
        constraints=[],
        assumptions=["assumed X"],
    )


def _make_state(requirements=None):
    return {
        "session_id": "test-session-123",
        "raw_prompt": "build me an agent",
        "requirements": requirements or _make_requirements(),
        "requirements_approved": False,
        "human_answers": [],
        "elicitor_questions": [],
    }


# ── Checkpoint Node Tests ────────────────────────────────────────────


class TestHumanCheckpointRequirements:
    """Tests for the human_checkpoint_requirements graph node."""

    @patch("app.pipeline.checkpoints.interrupt")
    def test_approved_flow(self, mock_interrupt):
        """When interrupt returns approved=True, node sets requirements_approved."""
        mock_interrupt.return_value = {"approved": True}
        state = _make_state()
        result = human_checkpoint_requirements(state)
        assert result["requirements_approved"] is True

    @patch("app.pipeline.checkpoints.interrupt")
    def test_interrupt_receives_checkpoint_payload(self, mock_interrupt):
        """interrupt() is called with checkpoint_type and requirements."""
        mock_interrupt.return_value = {"approved": True}
        reqs = _make_requirements()
        state = _make_state(reqs)
        human_checkpoint_requirements(state)

        call_args = mock_interrupt.call_args[0][0]
        assert call_args["checkpoint_type"] == "requirements"
        assert call_args["requirements"]["domain"] == "test-domain"

    @patch("app.pipeline.checkpoints.interrupt")
    def test_default_approval_on_unknown_result(self, mock_interrupt):
        """If interrupt returns unexpected value, default to approved."""
        mock_interrupt.return_value = "unexpected"
        state = _make_state()
        result = human_checkpoint_requirements(state)
        assert result["requirements_approved"] is True

    @patch("app.pipeline.checkpoints.interrupt")
    @patch("app.pipeline.checkpoints.elicitor_agent", create=True)
    def test_corrections_flow(self, mock_elicitor, mock_interrupt):
        """When corrections provided, elicitor re-runs."""
        mock_interrupt.return_value = {"corrections": "fix the inputs"}
        mock_elicitor_result = {
            "requirements": _make_requirements(),
            "requirements_approved": False,
        }

        with patch("app.agents.elicitor.elicitor_agent", return_value=mock_elicitor_result):
            state = _make_state()
            result = human_checkpoint_requirements(state)
            assert result["requirements_approved"] is False

    @patch("app.pipeline.checkpoints.interrupt")
    def test_corrections_added_to_answers(self, mock_interrupt):
        """Corrections are appended to human_answers before re-run."""
        mock_interrupt.return_value = {"corrections": "change the domain"}

        with patch("app.agents.elicitor.elicitor_agent") as mock_elic:
            mock_elic.return_value = {
                "requirements": _make_requirements(),
                "requirements_approved": False,
            }
            state = _make_state()
            state["human_answers"] = [{"round": 1, "answers": "original answer", "timestamp": ""}]
            human_checkpoint_requirements(state)

            # elicitor_agent should be called with extended answers
            call_state = mock_elic.call_args[0][0]
            assert len(call_state["human_answers"]) == 2
            assert call_state["human_answers"][-1]["round"] == "correction"
            assert call_state["human_answers"][-1]["answers"] == "change the domain"


# ── Approve Endpoint Tests ───────────────────────────────────────────


class TestApproveEndpoint:
    """Tests for POST /sessions/{id}/approve."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def test_approve_404_unknown_session(self, client):
        res = client.post(
            "/sessions/nonexistent/approve",
            json={"checkpoint": "requirements", "approved": True},
        )
        assert res.status_code == 404

    def test_approve_request_validation(self, client):
        """Invalid checkpoint type rejected."""
        res = client.post(
            "/sessions/nonexistent/approve",
            json={"checkpoint": "invalid", "approved": True},
        )
        assert res.status_code == 422  # Pydantic validation error


# ── Graph Compilation Tests ──────────────────────────────────────────


class TestGraphCompilation:
    """Tests that the graph compiles with checkpointer and checkpoint nodes."""

    def test_compiled_graph_exists(self):
        from app.pipeline.graph import compiled_graph
        assert compiled_graph is not None

    def test_graph_has_checkpoint_node(self):
        from app.pipeline.graph import build_graph
        graph = build_graph()
        # StateGraph stores nodes internally
        assert "human_review_requirements" in graph.nodes

    def test_graph_has_checkpointer(self):
        from app.pipeline.graph import compiled_graph
        assert compiled_graph.checkpointer is not None
