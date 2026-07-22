"""Service-level end-to-end test for ReviewService (offline, on fakes)."""

import asyncio
from collections.abc import Mapping

from bicho.application.analyzers.base import Analyzer
from bicho.application.analyzers.correctness import build_correctness_analyzer
from bicho.application.analyzers.schemas import AnalyzerReport, RawFinding
from bicho.application.graph.builder import build_graph
from bicho.application.review_service import ReviewService
from bicho.domain.models.finding import Confidence, Severity
from bicho.domain.models.pull_request import ChangedFile, PullRequest
from bicho.domain.models.review import ReviewOptions, ReviewRequest, ReviewStatus
from bicho.domain.ports.model_provider import ok_result
from bicho.infrastructure.diff.hunk_parser import DiffParser
from bicho.infrastructure.github.fake import FakeGitHub
from bicho.infrastructure.ids import UuidGenerator
from bicho.infrastructure.language.generic import GenericAdapter
from bicho.infrastructure.language.registry import AdapterRegistry
from bicho.infrastructure.model.fake import FakeModelProvider

_PATCH = "@@ -10,3 +10,4 @@\n ctx\n-old\n+new_a\n+new_b\n"


def _raw(subcategory: str, confidence: Confidence, line: int) -> RawFinding:
    return RawFinding(
        title="Bug",
        explanation="e",
        impact="i",
        recommendation="r",
        path="app/db.py",
        start_line=line,
        end_line=line,
        severity=Severity.HIGH,
        confidence=confidence,
        subcategory=subcategory,
        snippet="new_a",
    )


async def test_review_service_runs_end_to_end_and_returns_a_result() -> None:
    pull_request = PullRequest(
        repository="o/r", number=1, head_sha="sha", base_ref="main", title="T"
    )
    github = FakeGitHub(
        pull_request=pull_request,
        changed_files=(ChangedFile(filename="app/db.py", status="modified", patch=_PATCH),),
    )
    report = AnalyzerReport(
        findings=(
            _raw("off-by-one", Confidence.HIGH, 11),
            _raw("unused-var", Confidence.LOW, 12),
        )
    )
    model = FakeModelProvider([ok_result(report, model_id="fake")])
    analyzers: Mapping[str, Analyzer] = {
        "correctness": build_correctness_analyzer(model=model, ids=UuidGenerator())
    }
    service = ReviewService(
        graph=build_graph(["correctness"]),
        github=github,
        diff_parser=DiffParser(),
        adapters=AdapterRegistry([], fallback=GenericAdapter()),
        analyzers=analyzers,
        ids=UuidGenerator(),
    )

    result = await service.run(ReviewRequest(repository="o/r", pr_number=1), ReviewOptions())

    assert result.status is ReviewStatus.COMPLETED
    assert result.review_id is not None
    assert len(github.published) == 1
    assert result.total_count == 2
    assert result.confirmed_count == 1
    assert result.draft is not None
    assert len(result.draft.inline_comments) == 1


async def test_run_fails_cleanly_when_it_exceeds_the_deadline() -> None:
    class _SlowGraph:
        async def ainvoke(self, initial: object, *, context: object) -> dict[str, object]:
            await asyncio.sleep(1)
            return {}

    service = ReviewService(
        graph=_SlowGraph(),
        github=FakeGitHub(),
        diff_parser=DiffParser(),
        adapters=AdapterRegistry([], fallback=GenericAdapter()),
        analyzers={},
        ids=UuidGenerator(),
        timeout_seconds=0.01,
    )

    result = await service.run(ReviewRequest(repository="o/r", pr_number=1), ReviewOptions())

    assert result.status is ReviewStatus.FAILED
