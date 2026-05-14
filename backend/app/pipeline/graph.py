"""LangGraph pipeline graph definition for Frankenstein.

Six-stage StateGraph with two human checkpoints and two feedback loops:

  elicitor → [human_review_requirements] → architect → critic
                                              ↑            │
                                              └── (criticals > 0)
                                                           │
                                              (no criticals)
                                                           ▼
                                          [human_review_spec] → builder → tester
                                                                  ↑          │
                                                    (code-level fix) ────────┤
                                              ↑                              │
                                    (spec-level fix) ────────────────────────┤
                                                                             │
                                                                  (all pass) │
                                                                             ▼
                                                                          learner → END
"""

import logging

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agents.architect import architect_agent
from app.agents.builder import builder_agent
from app.agents.critic import critic_agent
from app.agents.elicitor import elicitor_agent
from app.agents.learner import learner_agent
from app.agents.tester import tester_agent
from app.config import settings
from app.models.state import FrankensteinState

logger = logging.getLogger(__name__)


# ── Human Checkpoints ─────────────────────────────────────────────────

from app.pipeline.checkpoints import (  # noqa: E402
    human_checkpoint_requirements,
    human_checkpoint_spec,
)


# ── Routing Functions ─────────────────────────────────────────────────


def route_after_critique(state: FrankensteinState) -> str:
    """Critic → Architect (loop on criticals) or → human_review_spec."""
    critique = state.get("critique")
    if not critique:
        return "human_review_spec"

    criticals = [f for f in critique.findings if f.severity == "critical"]
    iteration = state.get("spec_iteration", 0)
    max_iter = settings.max_spec_iterations

    if criticals and iteration < max_iter:
        logger.info(
            "Routing: critic → architect (criticals=%d, iteration=%d/%d)",
            len(criticals),
            iteration,
            max_iter,
        )
        return "architect"

    logger.info("Routing: critic → human_review_spec")
    return "human_review_spec"


def route_after_test(state: FrankensteinState) -> str:
    """Tester → learner (pass) | builder (code fix) | architect (spec fix)."""
    test_results = state.get("test_results")
    if not test_results:
        return "learner"

    if test_results.all_passed:
        logger.info("Routing: tester → learner (all passed)")
        return "learner"

    iteration = state.get("build_iteration", 0)
    max_iter = settings.max_build_iterations

    if iteration >= max_iter:
        logger.info(
            "Routing: tester → learner (max iterations %d reached)",
            max_iter,
        )
        return "learner"

    # Check failure traces for root cause level
    failure_traces = state.get("failure_traces", [])
    for trace in failure_traces:
        if trace.root_cause_level == "spec":
            logger.info("Routing: tester → architect (spec-level failure)")
            return "architect"

    logger.info("Routing: tester → builder (code-level fix)")
    return "builder"


# ── Graph Construction ────────────────────────────────────────────────


def build_graph() -> StateGraph:
    """Build the complete Frankenstein pipeline graph."""
    graph = StateGraph(FrankensteinState)

    # Nodes
    graph.add_node("elicitor", elicitor_agent)
    graph.add_node("human_review_requirements", human_checkpoint_requirements)
    graph.add_node("architect", architect_agent)
    graph.add_node("critic", critic_agent)
    graph.add_node("human_review_spec", human_checkpoint_spec)
    graph.add_node("builder", builder_agent)
    graph.add_node("tester", tester_agent)
    graph.add_node("learner", learner_agent)

    # Linear edges
    graph.set_entry_point("elicitor")
    graph.add_edge("elicitor", "human_review_requirements")
    graph.add_edge("human_review_requirements", "architect")
    graph.add_edge("architect", "critic")
    graph.add_edge("human_review_spec", "builder")
    graph.add_edge("builder", "tester")
    graph.add_edge("learner", END)

    # Conditional edges (feedback loops)
    graph.add_conditional_edges(
        "critic",
        route_after_critique,
        {"architect": "architect", "human_review_spec": "human_review_spec"},
    )
    graph.add_conditional_edges(
        "tester",
        route_after_test,
        {"learner": "learner", "builder": "builder", "architect": "architect"},
    )

    return graph


checkpointer = MemorySaver()
compiled_graph = build_graph().compile(checkpointer=checkpointer)
