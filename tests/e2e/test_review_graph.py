"""End-to-end tests for the review graph, driven entirely by fakes (offline)."""

from collections.abc import Mapping

from bicho.application.analyzers.base import AnalysisContext, Analyzer
from bicho.application.analyzers.correctness import build_correctness_analyzer
from bicho.application.analyzers.schemas import AnalyzerReport, RawFinding
from bicho.application.context import ReviewContext
from bicho.application.graph.builder import build_graph, run_graph
from bicho.application.graph.state import ReviewState
from bicho.domain.models.analysis import AnalyzerOutcome, OutcomeStatus
from bicho.domain.models.diff import FileChangeKind
from bicho.domain.models.finding import Category, Confidence, Severity
from bicho.domain.models.pull_request import ChangedFile, PullRequest
from bicho.domain.models.review import ReviewOptions, ReviewRequest
from bicho.domain.ports.github import GitHubPort
from bicho.domain.ports.model_provider import ok_result
from bicho.infrastructure.diff.hunk_parser import DiffParser
from bicho.infrastructure.github.fake import FakeGitHub
from bicho.infrastructure.language.generic import GenericAdapter
from bicho.infrastructure.language.registry import AdapterRegistry
from bicho.infrastructure.model.fake import FakeModelProvider

_PATCH = "@@ -10,3 +10,4 @@\n ctx\n-old\n+new_a\n+new_b\n"


class _Ids:
    def __init__(self) -> None:
        self._n = 0

    def new_id(self) -> str:
        self._n += 1
        return f"id-{self._n}"


class _Boom:
    async def analyze(self, context: AnalysisContext) -> AnalyzerOutcome:
        raise RuntimeError("boom")


def _raw() -> RawFinding:
    return RawFinding(
        title="Bug",
        explanation="e",
        impact="i",
        recommendation="r",
        path="app/db.py",
        start_line=11,
        end_line=12,
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        subcategory="off-by-one",
        snippet="new_a",
    )


def _github(changed_files: tuple[ChangedFile, ...] | None = None) -> FakeGitHub:
    pull_request = PullRequest(
        repository="o/r", number=1, head_sha="sha", base_ref="main", title="T"
    )
    files = changed_files or (ChangedFile(filename="app/db.py", status="modified", patch=_PATCH),)
    return FakeGitHub(pull_request=pull_request, changed_files=files)


def _context(github: GitHubPort, analyzers: Mapping[str, Analyzer]) -> ReviewContext:
    return ReviewContext(
        github=github,
        diff_parser=DiffParser(),
        adapters=AdapterRegistry([], fallback=GenericAdapter()),
        analyzers=analyzers,
        options=ReviewOptions(),
        correlation_id="c",
    )


def _initial() -> ReviewState:
    return {"request": ReviewRequest(repository="o/r", pr_number=1), "outcomes": []}


async def test_graph_produces_findings() -> None:
    model = FakeModelProvider([ok_result(AnalyzerReport(findings=(_raw(),)), model_id="fake")])
    analyzers: Mapping[str, Analyzer] = {
        "correctness": build_correctness_analyzer(model=model, ids=_Ids())
    }

    result = await run_graph(
        build_graph(["correctness"]), _initial(), _context(_github(), analyzers)
    )

    findings = result["findings"]
    assert len(findings) == 1
    assert findings[0].category is Category.CORRECTNESS
    draft = result["review_draft"]
    assert len(draft.inline_comments) == 1
    assert draft.commit_id == "sha"


async def test_graph_degrades_when_an_analyzer_raises() -> None:
    analyzers: Mapping[str, Analyzer] = {"correctness": _Boom()}

    result = await run_graph(
        build_graph(["correctness"]), _initial(), _context(_github(), analyzers)
    )

    assert result["findings"] == []
    assert any(outcome.status is OutcomeStatus.ERROR for outcome in result["outcomes"])


async def test_graph_with_no_analyzers_selected() -> None:
    result = await run_graph(build_graph([]), _initial(), _context(_github(), {}))

    assert result["findings"] == []


async def test_graph_maps_file_statuses_and_binary() -> None:
    files = (
        ChangedFile(filename="a.py", status="added", patch="@@ -0,0 +1 @@\n+a\n"),
        ChangedFile(filename="b.py", status="removed", patch="@@ -1 +0,0 @@\n-b\n"),
        ChangedFile(filename="c.py", status="renamed", patch="@@ -1 +1 @@\n-c\n+d\n"),
        ChangedFile(filename="d.py", status="modified", patch="@@ -1 +1 @@\n-e\n+f\n"),
        ChangedFile(filename="img.png", status="added", patch=None),
    )

    result = await run_graph(build_graph([]), _initial(), _context(_github(files), {}))

    kinds = {file.path: file.change_kind for file in result["diff"].files}
    assert kinds["a.py"] is FileChangeKind.ADDED
    assert kinds["b.py"] is FileChangeKind.REMOVED
    assert kinds["c.py"] is FileChangeKind.RENAMED
    assert kinds["d.py"] is FileChangeKind.MODIFIED
    binary = result["diff"].file("img.png")
    assert binary is not None
    assert binary.is_binary is True
