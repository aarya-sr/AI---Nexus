from typing import Literal

from pydantic import BaseModel


class TestCase(BaseModel):
    name: str
    description: str = ""
    input_data: dict = {}
    expected_output_schema: dict = {}
    quality_checks: list[str] = []
    timeout: int = 60


class TestResult(BaseModel):
    test_name: str
    status: Literal["passed", "failed", "error"]
    duration_seconds: float = 0.0
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    output_parsed: dict | None = None
    validation_details: str = ""


class TestReport(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    all_passed: bool = False
    results: list[TestResult] = []


class FailureTrace(BaseModel):
    test_name: str
    error_type: Literal["crash", "wrong_output", "missing_field", "quality_fail"]
    raw_error: str
    failing_agent: str
    root_cause_level: Literal["code", "spec"]
    root_cause_analysis: str
    spec_decision_responsible: str
    suggested_fix: str
