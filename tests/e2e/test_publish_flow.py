"""End-to-end tests for the publish decision: dry-run, idempotency, force, and the stale-head guard.

Everything runs on fakes: ``FakeGitHub`` records what would be published and can simulate a head
that moves between analysis and publishing, so each branch of the guards is exercised offline.
"""

from collections.abc import Mapping

from bicho.application.analyzers.base import Analyzer
from bicho.application.analyzers.correctness import build_correctness_analyzer
from bicho.application.analyzers.schemas import AnalyzerReport, RawFinding
from bicho.application.graph.builder import build_graph
from bicho.application.graph.compose import WORKFLOW_VERSION
from bicho.application.review_service import ReviewService
from bicho.domain.models.finding import Confidence, Severity
from bicho.domain.models.marker import ReviewMarker
from bicho.domain.models.pull_request import ChangedFile, PullRequest
from bicho.domain.models.review import (
    ExistingReview,
    ReviewOptions,
    ReviewRequest,
    ReviewStatus,
)
from bicho.domain.ports.model_provider import ok_result
from bicho.infrastructure.diff.hunk_parser import DiffParser
from bicho.infrastructure.github.fake import FakeGitHub
from bicho.infrastructure.ids import UuidGenerator
from bicho.infrastructure.language.generic import GenericAdapter
from bicho.infrastructure.language.registry import AdapterRegistry
from bicho.infrastructure.model.fake import FakeModelProvider

_PATCH = "@@ -10,3 +10,4 @@\n ctx\n-old\n+new_a\n+new_b\n"


def _pull_request() -> PullRequest:
    return PullRequest(repository="o/r", number=1, head_sha="sha", base_ref="main", title="T")


def _report() -> AnalyzerReport:
    return AnalyzerReport(
        findings=(
            RawFinding(
                title="Off-by-one",
                explanation="e",
                impact="i",
                recommendation="r",
                path="app/db.py",
                start_line=11,
                end_line=11,
                severity=Severity.HIGH,
                confidence=Confidence.HIGH,
                subcategory="off-by-one",
                snippet="new_a",
            ),
        )
    )


def _marker_body(head_sha: str) -> str:
    marker = ReviewMarker(
        head_sha=head_sha,
        workflow_version=WORKFLOW_VERSION,
        run_fingerprint="rf",
        model_id="fake",
        prompt_version="v1",
    )
    return f"Bicho review\n{marker.render()}"


def _service(github: FakeGitHub) -> ReviewService:
    model = FakeModelProvider([ok_result(_report(), model_id="fake")])
    analyzers: Mapping[str, Analyzer] = {
        "correctness": build_correctness_analyzer(model=model, ids=UuidGenerator())
    }
    return ReviewService(
        graph=build_graph(["correctness"]),
        github=github,
        diff_parser=DiffParser(),
        adapters=AdapterRegistry([], fallback=GenericAdapter()),
        analyzers=analyzers,
        ids=UuidGenerator(),
    )


def _github(**kwargs: object) -> FakeGitHub:
    return FakeGitHub(
        pull_request=_pull_request(),
        changed_files=(ChangedFile(filename="app/db.py", status="modified", patch=_PATCH),),
        **kwargs,  # type: ignore[arg-type]
    )


async def test_dry_run_composes_without_publishing() -> None:
    github = _github()
    result = await _service(github).run(
        ReviewRequest(repository="o/r", pr_number=1), ReviewOptions(dry_run=True)
    )

    assert result.status is ReviewStatus.DRY_RUN
    assert result.review_id is None
    assert github.published == []


async def test_skips_when_head_already_reviewed() -> None:
    github = _github(
        reviews=(
            ExistingReview(id=1, author="someone", body="a human comment, no marker"),
            ExistingReview(id=2, author="bicho[bot]", body=_marker_body("sha")),
        )
    )
    result = await _service(github).run(
        ReviewRequest(repository="o/r", pr_number=1), ReviewOptions()
    )

    assert result.status is ReviewStatus.SKIPPED
    assert github.published == []


async def test_force_republishes_over_existing_marker() -> None:
    github = _github(reviews=(ExistingReview(id=2, author="bicho[bot]", body=_marker_body("sha")),))
    result = await _service(github).run(
        ReviewRequest(repository="o/r", pr_number=1), ReviewOptions(force=True)
    )

    assert result.status is ReviewStatus.COMPLETED
    assert len(github.published) == 1


async def test_stale_head_aborts_before_publishing() -> None:
    github = _github(moved_head_sha="newer-sha")
    result = await _service(github).run(
        ReviewRequest(repository="o/r", pr_number=1), ReviewOptions()
    )

    assert result.status is ReviewStatus.STALE
    assert github.published == []
