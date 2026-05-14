from typing import TypedDict

from app.models.code import CodeBundle
from app.models.critique import CritiqueReport
from app.models.learning import BuildOutcome
from app.models.requirements import RequirementsDoc
from app.models.spec import AgentSpec
from app.models.testing import FailureTrace, TestCase, TestReport
from app.models.tools import ToolSchema


class FrankensteinState(TypedDict, total=False):
    # Session
    session_id: str

    # Stage 1: Elicitor
    raw_prompt: str
    elicitor_questions: list[dict]
    human_answers: list[dict]
    requirements: RequirementsDoc
    requirements_approved: bool

    # Stage 2-3: Architect + Critic
    tool_library_matches: list[ToolSchema]
    past_spec_matches: list[dict]
    spec: AgentSpec
    architect_reasoning: str
    critique: CritiqueReport
    spec_iteration: int
    spec_approved: bool

    # Stage 4-5: Builder + Tester
    generated_code: CodeBundle
    test_cases: list[TestCase]
    test_results: TestReport
    failure_traces: list[FailureTrace]
    build_iteration: int

    # Stage 6: Learning
    build_outcome: BuildOutcome
