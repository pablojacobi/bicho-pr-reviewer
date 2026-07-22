"""Tests for finding deduplication."""

from collections.abc import Callable

from bicho.domain.models.finding import (
    Confidence,
    EvidenceRef,
    Finding,
    Severity,
    SourceKind,
    VerificationState,
)
from bicho.domain.services.dedup import deduplicate

FindingFactory = Callable[..., Finding]


def _survivor(findings: list[Finding]) -> Finding:
    return next(f for f in findings if f.verification_state is not VerificationState.DUPLICATE)


def test_distinct_fingerprints_are_all_kept(make_finding: FindingFactory) -> None:
    a = make_finding(id="a", fingerprint="fp-a")
    b = make_finding(id="b", fingerprint="fp-b")

    result = deduplicate([a, b])

    assert {f.id for f in result} == {"a", "b"}
    assert all(f.verification_state is not VerificationState.DUPLICATE for f in result)


def test_same_fingerprint_merges_to_highest_severity_survivor(make_finding: FindingFactory) -> None:
    high = make_finding(id="high", fingerprint="fp", severity=Severity.HIGH)
    low = make_finding(id="low", fingerprint="fp", severity=Severity.LOW)

    result = deduplicate([low, high])
    duplicates = [f for f in result if f.verification_state is VerificationState.DUPLICATE]

    assert _survivor(result).id == "high"
    assert [f.id for f in duplicates] == ["low"]
    assert duplicates[0].verification_reason == "merged into high"


def test_survivor_takes_max_severity_and_merged_evidence(make_finding: FindingFactory) -> None:
    ev1 = EvidenceRef(path="a.py", start_line=1, end_line=1, detail="one")
    ev2 = EvidenceRef(path="b.py", start_line=2, end_line=2, detail="two")
    a = make_finding(id="a", fingerprint="fp", severity=Severity.MEDIUM, evidence=(ev1,))
    b = make_finding(id="b", fingerprint="fp", severity=Severity.CRITICAL, evidence=(ev2,))

    survivor = _survivor(deduplicate([a, b]))

    assert survivor.severity is Severity.CRITICAL
    assert len(survivor.evidence) == 2
    assert ev1 in survivor.evidence
    assert ev2 in survivor.evidence


def test_corroboration_by_independent_source_raises_confidence(
    make_finding: FindingFactory,
) -> None:
    a = make_finding(
        id="a", fingerprint="fp", confidence=Confidence.LOW, source_kind=SourceKind.SEMGREP
    )
    b = make_finding(
        id="b", fingerprint="fp", confidence=Confidence.LOW, source_kind=SourceKind.LLM_ANALYZER
    )

    assert _survivor(deduplicate([a, b])).confidence is Confidence.MEDIUM


def test_same_source_does_not_raise_confidence(make_finding: FindingFactory) -> None:
    a = make_finding(
        id="a", fingerprint="fp", confidence=Confidence.LOW, source_kind=SourceKind.SEMGREP
    )
    b = make_finding(
        id="b",
        fingerprint="fp",
        confidence=Confidence.LOW,
        source_kind=SourceKind.SEMGREP,
        severity=Severity.LOW,
    )

    assert _survivor(deduplicate([a, b])).confidence is Confidence.LOW


def test_confidence_boost_caps_at_high(make_finding: FindingFactory) -> None:
    a = make_finding(
        id="a", fingerprint="fp", confidence=Confidence.HIGH, source_kind=SourceKind.SEMGREP
    )
    b = make_finding(
        id="b", fingerprint="fp", confidence=Confidence.HIGH, source_kind=SourceKind.LLM_ANALYZER
    )

    assert _survivor(deduplicate([a, b])).confidence is Confidence.HIGH


def test_deduplicate_is_order_independent(make_finding: FindingFactory) -> None:
    a = make_finding(
        id="a", fingerprint="fp", severity=Severity.HIGH, source_kind=SourceKind.SEMGREP
    )
    b = make_finding(id="b", fingerprint="fp", severity=Severity.LOW)
    c = make_finding(id="c", fingerprint="other")

    def summarize(findings: list[Finding]) -> list[tuple[str, str]]:
        return sorted((f.id, f.verification_state.value) for f in findings)

    assert summarize(deduplicate([a, b, c])) == summarize(deduplicate([c, b, a]))
