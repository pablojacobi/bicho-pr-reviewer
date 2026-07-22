"""Tests for the review-event severity policy."""

from collections.abc import Callable

from bicho.domain.models.finding import Finding, Severity
from bicho.domain.models.review import ReviewEvent
from bicho.domain.services.severity_policy import review_event


def test_request_changes_for_high_or_critical(make_finding: Callable[..., Finding]) -> None:
    assert review_event([make_finding(severity=Severity.HIGH)]) is ReviewEvent.REQUEST_CHANGES
    assert review_event([make_finding(severity=Severity.CRITICAL)]) is ReviewEvent.REQUEST_CHANGES


def test_comment_for_lower_severities_or_none(make_finding: Callable[..., Finding]) -> None:
    assert review_event([make_finding(severity=Severity.MEDIUM)]) is ReviewEvent.COMMENT
    assert review_event([]) is ReviewEvent.COMMENT
