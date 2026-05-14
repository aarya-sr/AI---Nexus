from typing import Literal

from pydantic import BaseModel


class Finding(BaseModel):
    vector: str
    severity: Literal["critical", "warning", "suggestion"]
    description: str
    location: str
    evidence: str
    suggested_fix: str


class CritiqueReport(BaseModel):
    findings: list[Finding]
    summary: str
    iteration: int
