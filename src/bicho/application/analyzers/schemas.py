"""Pydantic schemas for LLM analyzer output — the model boundary.

The model returns an ``AnalyzerReport`` via function calling; the base analyzer validates it and
normalizes each ``RawFinding`` into a domain ``Finding`` (assigning ids, fingerprints, metadata).
"""

from pydantic import BaseModel, Field

from bicho.domain.models.finding import Confidence, Severity


class RawFinding(BaseModel):
    """A single finding as produced by an analyzer model, before normalization."""

    title: str
    explanation: str
    impact: str
    recommendation: str
    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    severity: Severity
    confidence: Confidence
    subcategory: str
    snippet: str = ""


class AnalyzerReport(BaseModel):
    """The full structured output of an analyzer model."""

    findings: tuple[RawFinding, ...] = ()
