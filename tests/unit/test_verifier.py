"""Tests for the finding verifier (deterministic policy and the batched LLM verifier)."""

from collections.abc import Callable

from bicho.application.verifier import (
    FindingVerdict,
    LLMFindingVerifier,
    PolicyVerifier,
    VerificationReport,
)
from bicho.domain.models.diff import NormalizedDiff
from bicho.domain.models.finding import Confidence, Finding, VerificationState
from bicho.domain.ports.model_provider import error_result, ok_result
from bicho.infrastructure.model.fake import FakeModelProvider

_DIFF = NormalizedDiff(files=())


def _candidate(make_finding: Callable[..., Finding], **overrides: object) -> Finding:
    return make_finding(verification_state=VerificationState.CANDIDATE, **overrides)


async def test_policy_verifier_applies_the_confidence_policy(
    make_finding: Callable[..., Finding],
) -> None:
    findings = [
        _candidate(make_finding, id="a", confidence=Confidence.HIGH),
        _candidate(make_finding, id="b", confidence=Confidence.LOW),
    ]

    result = await PolicyVerifier().verify(findings, diff=_DIFF, correlation_id="c")

    assert result[0].verification_state is VerificationState.CONFIRMED
    assert result[1].verification_state is VerificationState.REJECTED


async def test_llm_verifier_skips_the_model_when_there_are_no_candidates(
    make_finding: Callable[..., Finding],
) -> None:
    verifier = LLMFindingVerifier(model=FakeModelProvider())
    findings = [make_finding(verification_state=VerificationState.DUPLICATE)]

    result = await verifier.verify(findings, diff=_DIFF, correlation_id="c")

    assert result == findings


async def test_llm_verifier_applies_verdicts(make_finding: Callable[..., Finding]) -> None:
    report = VerificationReport(
        verdicts=(
            FindingVerdict(index=0, keep=True, reason="real bug"),
            FindingVerdict(index=1, keep=False, reason="false positive"),
        )
    )
    verifier = LLMFindingVerifier(model=FakeModelProvider([ok_result(report, model_id="v")]))
    findings = [
        _candidate(make_finding, id="a"),
        _candidate(make_finding, id="b"),
        _candidate(make_finding, id="c", confidence=Confidence.HIGH),  # no verdict -> policy
        make_finding(id="d", verification_state=VerificationState.DUPLICATE),  # passthrough
    ]

    result = await verifier.verify(findings, diff=_DIFF, correlation_id="c")

    assert result[0].verification_state is VerificationState.CONFIRMED
    assert result[0].verification_reason == "real bug"
    assert result[1].verification_state is VerificationState.REJECTED
    assert result[2].verification_state is VerificationState.CONFIRMED  # policy fallback (HIGH)
    assert result[3].verification_state is VerificationState.DUPLICATE  # untouched


async def test_llm_verifier_falls_back_to_policy_on_model_failure(
    make_finding: Callable[..., Finding],
) -> None:
    verifier = LLMFindingVerifier(model=FakeModelProvider([error_result("boom", model_id="v")]))
    findings = [
        _candidate(make_finding, id="a", confidence=Confidence.HIGH),
        make_finding(id="d", verification_state=VerificationState.DUPLICATE),
    ]

    result = await verifier.verify(findings, diff=_DIFF, correlation_id="c")

    assert result[0].verification_state is VerificationState.CONFIRMED  # policy
    assert result[1].verification_state is VerificationState.DUPLICATE  # untouched
