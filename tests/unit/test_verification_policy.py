"""Tests for the first-pass verification policy."""

from collections.abc import Callable

from bicho.domain.models.finding import Confidence, Finding, VerificationState
from bicho.domain.services.verification_policy import verify


def test_confirms_medium_and_high_confidence(make_finding: Callable[..., Finding]) -> None:
    for confidence in (Confidence.MEDIUM, Confidence.HIGH):
        result = verify(make_finding(confidence=confidence))
        assert result.verification_state is VerificationState.CONFIRMED
        assert result.verification_reason is not None


def test_rejects_low_confidence(make_finding: Callable[..., Finding]) -> None:
    result = verify(make_finding(confidence=Confidence.LOW))

    assert result.verification_state is VerificationState.REJECTED
    assert result.verification_reason is not None
