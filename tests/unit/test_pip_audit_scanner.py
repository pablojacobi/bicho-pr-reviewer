"""Tests for the pip-audit dependency scanner (offline: real temp workspace, faked subprocess)."""

from bicho.application.analyzers.base import AnalysisContext
from bicho.domain.models.analysis import OutcomeStatus
from bicho.domain.models.diff import NormalizedDiff
from bicho.domain.models.finding import Category, SourceKind
from bicho.domain.ports.system import ProcessResult
from bicho.infrastructure.fs.workspace import TempWorkspaceFactory
from bicho.infrastructure.language.generic import GenericAdapter
from bicho.infrastructure.process.fake import FakeSubprocessRunner
from bicho.infrastructure.scanners.pip_audit_runner import DependencyAuditScanner, _line_of

# requests is pinned in the manifest (anchored to its line); django is not (falls back to line 1).
_MANIFEST = "flask==0.12.0\nrequests==2.19.0\n"
_VULNS = (
    b'{"dependencies": ['
    b'{"name": "requests", "version": "2.19.0", "vulns": [{"id": "PYSEC-2018-28", '
    b'"fix_versions": ["2.20.0"], "description": "CRLF injection"}]}, '
    b'{"name": "django", "version": "1.0", "vulns": [{"id": "PYSEC-9", "fix_versions": []}]}]}'
)


class _Ids:
    def __init__(self) -> None:
        self._n = 0

    def new_id(self) -> str:
        self._n += 1
        return f"id-{self._n}"


def _context(file_contents: dict[str, str]) -> AnalysisContext:
    return AnalysisContext(
        diff=NormalizedDiff(files=()),
        head_sha="sha",
        language="python",
        framework=None,
        correlation_id="c",
        adapter=GenericAdapter(),
        file_contents=file_contents,
    )


def _process(
    *, stdout: bytes = b"", returncode: int | None = 0, timed_out: bool = False, stderr: bytes = b""
) -> ProcessResult:
    return ProcessResult(returncode=returncode, stdout=stdout, stderr=stderr, timed_out=timed_out)


def _scanner(result: ProcessResult) -> DependencyAuditScanner:
    return DependencyAuditScanner(
        runner=FakeSubprocessRunner(result), workspace=TempWorkspaceFactory(), ids=_Ids()
    )


def test_line_of_finds_pinned_package_or_falls_back() -> None:
    assert _line_of(_MANIFEST, "requests") == 2
    assert _line_of(_MANIFEST, "flask") == 1
    assert _line_of(_MANIFEST, "absent") == 1


async def test_no_manifest_changed_is_zero_findings_without_running() -> None:
    runner = FakeSubprocessRunner(_process())
    scanner = DependencyAuditScanner(runner=runner, workspace=TempWorkspaceFactory(), ids=_Ids())

    outcome = await scanner.analyze(_context({"app/db.py": "x = 1\n"}))

    assert outcome.status is OutcomeStatus.ZERO_FINDINGS
    assert runner.commands == []


async def test_maps_vulnerabilities_to_findings() -> None:
    outcome = await _scanner(_process(stdout=_VULNS, returncode=1)).analyze(
        _context({"requirements.txt": _MANIFEST})
    )

    assert outcome.status is OutcomeStatus.OK
    assert len(outcome.findings) == 2
    requests_finding = next(f for f in outcome.findings if "requests" in f.title)
    assert requests_finding.category is Category.DEPENDENCY
    assert requests_finding.source_kind is SourceKind.PIP_AUDIT
    assert requests_finding.subcategory == "PYSEC-2018-28"
    assert requests_finding.start_line == 2  # anchored to the pinning line
    assert "2.20.0" in requests_finding.recommendation


async def test_clean_manifest_is_zero_findings() -> None:
    outcome = await _scanner(_process(stdout=b'{"dependencies": []}')).analyze(
        _context({"requirements.txt": _MANIFEST})
    )

    assert outcome.status is OutcomeStatus.ZERO_FINDINGS


async def test_timeout_degrades() -> None:
    outcome = await _scanner(_process(timed_out=True, returncode=None)).analyze(
        _context({"requirements.txt": _MANIFEST})
    )

    assert outcome.status is OutcomeStatus.TIMEOUT
    assert outcome.degraded


async def test_error_exit_degrades_with_stderr() -> None:
    outcome = await _scanner(_process(returncode=2, stderr=b"network down")).analyze(
        _context({"requirements.txt": _MANIFEST})
    )

    assert outcome.status is OutcomeStatus.ERROR
    assert outcome.diagnostics[0].message == "network down"


async def test_unparseable_output_degrades() -> None:
    outcome = await _scanner(_process(stdout=b"not json")).analyze(
        _context({"requirements.txt": _MANIFEST})
    )

    assert outcome.status is OutcomeStatus.ERROR
