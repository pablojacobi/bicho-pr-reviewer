"""Decide the GitHub review event from the confirmed findings."""

from collections.abc import Sequence

from bicho.domain.models.finding import Finding, Severity
from bicho.domain.models.review import ReviewEvent

_REQUEST_CHANGES_AT = frozenset({Severity.HIGH, Severity.CRITICAL})


def review_event(findings: Sequence[Finding]) -> ReviewEvent:
    """REQUEST_CHANGES if any finding is high/critical, otherwise a plain COMMENT."""
    if any(finding.severity in _REQUEST_CHANGES_AT for finding in findings):
        return ReviewEvent.REQUEST_CHANGES
    return ReviewEvent.COMMENT
