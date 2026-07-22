"""End-to-end: a pip-audit finding flows through the graph fan-out into the review draft."""

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
from bicho.infrastructure.scanners.pip_audit_runner import DependencyAuditScanner

_PATCH = "@@ -0,0 +1 @@\n+requests==2.19.0\n"
_VULNS = (
    b'{"dependencies": [{"name": "requests", "version": "2.19.0", '
    b'"vulns": [{"id": "PYSEC-2018-28", "fix_versions": ["2.20.0"], "description": "CRLF"}]}]}'
)


async def test_pip_audit_finding_reaches_the_draft() -> None:
    github = FakeGitHub(
        pull_request=PullRequest(
            repository="o/r", number=1, head_sha="sha", base_ref="main", title="T"
        ),
        changed_files=(ChangedFile(filename="requirements.txt", status="modified", patch=_PATCH),),
        file_contents={"requirements.txt": "requests==2.19.0\n"},
    )
    scanner = DependencyAuditScanner(
        runner=FakeSubprocessRunner(
            ProcessResult(returncode=1, stdout=_VULNS, stderr=b"", timed_out=False)
        ),
        workspace=TempWorkspaceFactory(),
        ids=UuidGenerator(),
    )
    analyzers: Mapping[str, Analyzer] = {"pip-audit": scanner}
    service = ReviewService(
        graph=build_graph(["pip-audit"]),
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
    assert result.draft.inline_comments[0].path == "requirements.txt"
