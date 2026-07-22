"""Tests for the normalized Finding domain model."""

import pytest
from pydantic import ValidationError

from bicho.domain.models.finding import (
    Category,
    Confidence,
    DiffSide,
    EvidenceRef,
    Finding,
    Severity,
    SourceKind,
    VerificationState,
)


def _finding(**overrides: object) -> Finding:
    data: dict[str, object] = {
        "id": "f1",
        "fingerprint": "abc0123456789def",
        "category": Category.SECURITY,
        "subcategory": "sql-injection",
        "severity": Severity.HIGH,
        "confidence": Confidence.HIGH,
        "title": "SQL injection via string interpolation",
        "explanation": "User input is interpolated into a SQL string.",
        "impact": "An attacker can read or modify arbitrary rows.",
        "recommendation": "Use parameterized queries.",
        "path": "app/db.py",
        "start_line": 10,
        "end_line": 12,
        "source_kind": SourceKind.LLM_ANALYZER,
        "source_name": "security",
        "head_sha": "deadbeef",
        "language": "python",
    }
    data.update(overrides)
    return Finding.model_validate(data)


def test_confirmed_finding_publishes_inline() -> None:
    finding = _finding(verification_state=VerificationState.CONFIRMED)

    assert finding.is_confirmed is True
    assert finding.publish_inline is True
    assert finding.publish_in_summary is False


def test_candidate_finding_is_not_published() -> None:
    finding = _finding()  # default state is CANDIDATE

    assert finding.is_confirmed is False
    assert finding.publish_inline is False
    assert finding.publish_in_summary is False


def test_confirmed_summary_only_finding_goes_to_summary() -> None:
    finding = _finding(verification_state=VerificationState.CONFIRMED, summary_only=True)

    assert finding.publish_inline is False
    assert finding.publish_in_summary is True


def test_confirmed_unanchorable_finding_goes_to_summary() -> None:
    finding = _finding(verification_state=VerificationState.CONFIRMED, can_publish_inline=False)

    assert finding.publish_inline is False
    assert finding.publish_in_summary is True


def test_finding_is_frozen() -> None:
    finding = _finding()

    with pytest.raises(ValidationError):
        finding.severity = Severity.LOW


def test_finding_rejects_inverted_line_range() -> None:
    with pytest.raises(ValidationError):
        _finding(start_line=20, end_line=10)


def test_finding_accepts_equal_line_range() -> None:
    finding = _finding(start_line=7, end_line=7)

    assert finding.start_line == finding.end_line == 7


def test_default_diff_side_is_right() -> None:
    assert _finding().diff_side is DiffSide.RIGHT


def test_severity_rank_is_totally_ordered() -> None:
    ranks = [Severity.INFO.rank, Severity.LOW.rank, Severity.MEDIUM.rank, Severity.HIGH.rank]
    assert ranks == sorted(ranks)
    assert Severity.CRITICAL.rank > Severity.HIGH.rank


def test_evidence_ref_holds_a_location() -> None:
    ref = EvidenceRef(
        path="app/callers.py", start_line=3, end_line=5, detail="caller passes raw input"
    )

    assert ref.path == "app/callers.py"
    assert (ref.start_line, ref.end_line) == (3, 5)
