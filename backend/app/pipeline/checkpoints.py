"""Human checkpoint nodes for the Frankenstein pipeline.

Uses LangGraph interrupt() to pause for human review at two points:
  1. After Elicitor — requirements approval
  2. After Critic — spec approval (Story 2.4)
"""

import logging

from langgraph.types import interrupt

from app.models.state import FrankensteinState

logger = logging.getLogger(__name__)


def human_checkpoint_requirements(state: FrankensteinState) -> dict:
    """Checkpoint 1: pause for human requirements review.

    Sends the RequirementsDoc via interrupt payload so the orchestrator
    can forward it over WebSocket.  The approve endpoint resumes with
    Command(resume={"approved": True}) or injects corrections.
    """
    requirements = state.get("requirements")
    session_id = state.get("session_id", "")

    payload = {
        "checkpoint_type": "requirements",
        "requirements": requirements.model_dump() if requirements else {},
    }

    logger.info("[%s] Checkpoint 1 — pausing for requirements review", session_id)

    result = interrupt(payload)

    if isinstance(result, dict) and result.get("approved"):
        logger.info("[%s] Requirements approved — continuing to architect", session_id)
        return {"requirements_approved": True}

    # Edit flow: corrections provided, re-run elicitor
    if isinstance(result, dict) and result.get("corrections"):
        corrections = result["corrections"]
        logger.info("[%s] Requirements corrections received — re-running elicitor", session_id)

        current_answers = list(state.get("human_answers", []))
        current_answers.append({
            "round": "correction",
            "answers": corrections,
            "timestamp": "",
        })

        from app.agents.elicitor import elicitor_agent

        updated = elicitor_agent({
            **state,
            "human_answers": current_answers,
        })

        return {
            **updated,
            "requirements_approved": False,
        }

    # Default: treat as approved
    logger.info("[%s] Requirements review — defaulting to approved", session_id)
    return {"requirements_approved": True}


def human_checkpoint_spec(state: FrankensteinState) -> dict:
    """Checkpoint 2: pause for human spec + critique review.

    Sends the AgentSpec and CritiqueReport via interrupt payload.
    Resume with Command(resume={"approved": True}) or feedback for revision.
    """
    spec = state.get("spec")
    critique = state.get("critique")
    reasoning = state.get("architect_reasoning", "")
    session_id = state.get("session_id", "")

    payload = {
        "checkpoint_type": "spec",
        "spec": spec.model_dump() if spec else {},
        "critique": critique.model_dump() if critique else {},
        "architect_reasoning": reasoning,
    }

    logger.info("[%s] Checkpoint 2 — pausing for spec review", session_id)

    result = interrupt(payload)

    if isinstance(result, dict) and result.get("approved"):
        logger.info("[%s] Spec approved — continuing to builder", session_id)
        return {"spec_approved": True}

    # Feedback flow: user provides free-text, triggers architect revision
    if isinstance(result, dict) and result.get("feedback"):
        feedback = result["feedback"]
        logger.info("[%s] Spec feedback received — triggering revision", session_id)

        from app.models.critique import CritiqueReport, Finding

        # Inject user feedback as a critical finding so architect addresses it
        user_finding = Finding(
            vector="human_feedback",
            severity="critical",
            description=f"User feedback: {feedback}",
            location="spec (user review)",
            evidence="Direct user input at checkpoint 2",
            suggested_fix=feedback,
        )

        existing_findings = list(critique.findings) if critique else []
        existing_findings.append(user_finding)

        return {
            "spec_approved": False,
            "critique": CritiqueReport(
                findings=existing_findings,
                summary=f"User requested changes: {feedback}",
                iteration=critique.iteration if critique else 1,
            ),
        }

    # Default: treat as approved
    logger.info("[%s] Spec review — defaulting to approved", session_id)
    return {"spec_approved": True}
