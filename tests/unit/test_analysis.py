"""Tests for analyzer/scanner outcomes."""

from collections.abc import Callable

from bicho.domain.models.analysis import AnalyzerOutcome, Diagnostic, OutcomeStatus
from bicho.domain.models.finding import Finding


def test_diagnostic_construction() -> None:
    diagnostic = Diagnostic(source="semgrep", status=OutcomeStatus.TIMEOUT, message="timed out")

    assert diagnostic.status is OutcomeStatus.TIMEOUT


def test_outcome_with_findings_is_not_degraded(make_finding: Callable[..., Finding]) -> None:
    outcome = AnalyzerOutcome(
        source="security", status=OutcomeStatus.OK, findings=(make_finding(),)
    )

    assert len(outcome.findings) == 1
    assert outcome.degraded is False


def test_zero_findings_is_not_degraded() -> None:
    assert AnalyzerOutcome(source="s", status=OutcomeStatus.ZERO_FINDINGS).degraded is False


def test_error_timeout_and_skipped_are_degraded() -> None:
    for status in (OutcomeStatus.ERROR, OutcomeStatus.TIMEOUT, OutcomeStatus.SKIPPED):
        outcome = AnalyzerOutcome(
            source="s",
            status=status,
            diagnostics=(Diagnostic(source="s", status=status, message="m"),),
        )

        assert outcome.degraded is True
