"""LangGraph pipeline graph definition for Frankenstein."""

from langgraph.graph import StateGraph

from app.agents.elicitor import elicitor_agent
from app.models.state import FrankensteinState


def _human_checkpoint_requirements(state: FrankensteinState) -> dict:
    """Stub checkpoint node — implemented in Story 1.4."""
    return {}


def build_graph() -> StateGraph:
    """Build and return the compiled Frankenstein pipeline graph."""
    graph = StateGraph(FrankensteinState)

    graph.add_node("elicitor", elicitor_agent)
    graph.add_node("human_review_requirements", _human_checkpoint_requirements)

    graph.set_entry_point("elicitor")
    graph.add_edge("elicitor", "human_review_requirements")

    return graph


compiled_graph = build_graph().compile()
