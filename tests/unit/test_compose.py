"""Tests for the review composer."""

from collections.abc import Callable

from bicho.application.graph.compose import compose_review_draft
from bicho.domain.models.analysis import AnalyzerOutcome, Diagnostic, OutcomeStatus
from bicho.domain.models.diff import NormalizedDiff
from bicho.domain.models.finding import Finding, Severity, VerificationState
from bicho.domain.models.marker import ReviewMarker
from bicho.domain.models.pull_request import PullRequest
from bicho.domain.models.review import ReviewEvent

FindingFactory = Callable[..., Finding]


def _pr() -> PullRequest:
    return PullRequest(repository="o/r", number=1, head_sha="sha", base_ref="main", title="T")


def _confirmed(make_finding: FindingFactory, **overrides: object) -> Finding:
    return make_finding(verification_state=VerificationState.CONFIRMED, **overrides)


def test_single_line_inline_comment_and_marker(
    make_finding: FindingFactory, sample_diff: NormalizedDiff
) -> None:
    finding = _confirmed(make_finding, start_line=11, end_line=11, model_id="m")

    draft = compose_review_draft(
        findings=[finding], diff=sample_diff, pull_request=_pr(), outcomes=[]
    )

    assert len(draft.inline_comments) == 1
    assert draft.inline_comments[0].is_multiline is False
    assert "confirmed finding" in draft.summary
    assert ReviewMarker.parse(draft.summary) is not None
    assert draft.commit_id == "sha"


def test_multiline_comment_and_request_changes(
    make_finding: FindingFactory, sample_diff: NormalizedDiff
) -> None:
    finding = _confirmed(make_finding, start_line=10, end_line=12, severity=Severity.HIGH)

    draft = compose_review_draft(
        findings=[finding], diff=sample_diff, pull_request=_pr(), outcomes=[]
    )

    assert draft.inline_comments[0].is_multiline is True
    assert draft.event is ReviewEvent.REQUEST_CHANGES


def test_unanchorable_finding_goes_to_summary(
    make_finding: FindingFactory, sample_diff: NormalizedDiff
) -> None:
    finding = _confirmed(make_finding, start_line=99, end_line=99)

    draft = compose_review_draft(
        findings=[finding], diff=sample_diff, pull_request=_pr(), outcomes=[]
    )

    assert draft.inline_comments == ()
    assert "not anchorable" in draft.summary


def test_no_confirmed_findings(make_finding: FindingFactory, sample_diff: NormalizedDiff) -> None:
    draft = compose_review_draft(
        findings=[make_finding()], diff=sample_diff, pull_request=_pr(), outcomes=[]
    )

    assert draft.inline_comments == ()
    assert "No confirmed issues found" in draft.summary
    assert draft.event is ReviewEvent.COMMENT


def test_degraded_outcomes_appear_in_summary(sample_diff: NormalizedDiff) -> None:
    outcome = AnalyzerOutcome(
        source="semgrep",
        status=OutcomeStatus.TIMEOUT,
        diagnostics=(
            Diagnostic(source="semgrep", status=OutcomeStatus.TIMEOUT, message="timed out"),
        ),
    )

    draft = compose_review_draft(
        findings=[], diff=sample_diff, pull_request=_pr(), outcomes=[outcome]
    )

    assert "Analysis notes" in draft.summary
    assert "timed out" in draft.summary
