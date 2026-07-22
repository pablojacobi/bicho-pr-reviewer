"""End-to-end: a Semgrep finding flows through the graph fan-out into the review draft."""

from collections.abc import Mapping

from bicho.application.analyzers.base import Analyzer
from bicho.application.graph.builder import build_graph
from bicho.application.review_service import ReviewService
from bicho.domain.models.pull_request import ChangedFile, PullRequest
from bicho.domain.models.review import ReviewOptions, ReviewRequest, ReviewStatus
from bicho.domain.ports.system import ProcessResult
from bicho.infrastructure.diff.hunk_parser import DiffParser
from bicho.infrastructure.fs.workspace import TempWorkspaceFactory
from bicho.infrastructure.github.fake import FakeGitHub
from bicho.infrastructure.ids import UuidGenerator
from bicho.infrastructure.language.generic import GenericAdapter
from bicho.infrastructure.language.registry import AdapterRegistry
from bicho.infrastructure.process.fake import FakeSubprocessRunner
from bicho.infrastructure.scanners.semgrep_runner import SemgrepScanner

_PATCH = "@@ -10,3 +10,4 @@\n ctx\n-old\n+eval(user_input)\n+new_b\n"
_FINDINGS = (
    b'{"results": [{"check_id": "python-eval-on-input", "path": "app/db.py", '
    b'"start": {"line": 11}, "end": {"line": 11}, '
    b'"extra": {"message": "eval is dangerous", "severity": "ERROR"}}]}'
)


async def test_semgrep_finding_reaches_the_draft() -> None:
    github = FakeGitHub(
        pull_request=PullRequest(
            repository="o/r", number=1, head_sha="sha", base_ref="main", title="T"
        ),
        changed_files=(ChangedFile(filename="app/db.py", status="modified", patch=_PATCH),),
        file_contents={"app/db.py": "eval(user_input)\n"},
    )
    scanner = SemgrepScanner(
        runner=FakeSubprocessRunner(
            ProcessResult(returncode=0, stdout=_FINDINGS, stderr=b"", timed_out=False)
        ),
        workspace=TempWorkspaceFactory(),
        ids=UuidGenerator(),
    )
    analyzers: Mapping[str, Analyzer] = {"semgrep": scanner}
    service = ReviewService(
        graph=build_graph(["semgrep"]),
        github=github,
        diff_parser=DiffParser(),
        adapters=AdapterRegistry([], fallback=GenericAdapter()),
        analyzers=analyzers,
        ids=UuidGenerator(),
    )

    result = await service.run(
        ReviewRequest(repository="o/r", pr_number=1), ReviewOptions(dry_run=True)
    )

    assert result.status is ReviewStatus.DRY_RUN
    assert result.total_count == 1
    assert result.confirmed_count == 1
    assert result.draft is not None
    assert result.draft.inline_comments[0].path == "app/db.py"
