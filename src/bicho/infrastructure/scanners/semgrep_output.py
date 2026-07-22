"""Pydantic models for the subset of Semgrep JSON output Bicho consumes.

Semgrep emits far more than this; extra keys are ignored. Validating the output as data means a
malformed payload surfaces as a parse error (a degraded outcome), never an exception mid-scan.
"""

from pydantic import BaseModel, ConfigDict, Field


class SemgrepPosition(BaseModel):
    """A 1-based line position within a file."""

    model_config = ConfigDict(extra="ignore")

    line: int = Field(ge=1)


class SemgrepExtra(BaseModel):
    """The message and severity a rule attaches to a match."""

    model_config = ConfigDict(extra="ignore")

    message: str = ""
    severity: str = "INFO"


class SemgrepResult(BaseModel):
    """One rule match."""

    model_config = ConfigDict(extra="ignore")

    check_id: str
    path: str
    start: SemgrepPosition
    end: SemgrepPosition
    extra: SemgrepExtra = SemgrepExtra()


class SemgrepOutput(BaseModel):
    """The top-level Semgrep JSON document."""

    model_config = ConfigDict(extra="ignore")

    results: list[SemgrepResult] = []
