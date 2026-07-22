"""Analyzer/scanner outcomes — the fan-in vocabulary of the review graph.

Every scanner and analyzer returns an ``AnalyzerOutcome`` instead of raising, so failures degrade
to a diagnostic rather than aborting the parallel superstep (LangGraph rolls a superstep back if any
branch raises). ``compose_review`` surfaces the diagnostics; nothing is hidden.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from bicho.domain.models.finding import Finding


class OutcomeStatus(StrEnum):
    """The result of running one analyzer or scanner."""

    OK = "ok"
    ZERO_FINDINGS = "zero_findings"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


_DEGRADED = frozenset({OutcomeStatus.ERROR, OutcomeStatus.TIMEOUT, OutcomeStatus.SKIPPED})


class Diagnostic(BaseModel):
    """A note about a degraded analyzer/scanner run, surfaced in the review summary."""

    model_config = ConfigDict(frozen=True)

    source: str
    status: OutcomeStatus
    message: str


class AnalyzerOutcome(BaseModel):
    """What one analyzer or scanner produced: findings, diagnostics, and a status."""

    model_config = ConfigDict(frozen=True)

    source: str
    status: OutcomeStatus
    findings: tuple[Finding, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

    @property
    def degraded(self) -> bool:
        """Whether this outcome is a failure/timeout/skip that should be surfaced to the reader."""
        return self.status in _DEGRADED
