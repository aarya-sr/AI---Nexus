from typing import Literal

from pydantic import BaseModel

from app.models.spec import AgentSpec
from app.models.testing import TestReport


class BuildOutcome(BaseModel):
    requirements_hash: str
    requirements_summary: str
    domain: str

    spec_snapshot: AgentSpec
    framework_used: str
    tools_used: list[str]

    test_results: TestReport
    iterations_needed: int
    total_time_seconds: float = 0.0

    success_patterns: list[str] = []
    failure_patterns: list[str] = []
    anti_patterns: list[str] = []
    lessons_learned: list[str] = []

    outcome: Literal["success", "partial_success", "failure"]
    partial_success_details: str | None = None
