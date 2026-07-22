"""Tests for the Semgrep scanner (offline: real temp workspace, faked subprocess)."""

from bicho.application.analyzers.base import AnalysisContext
from bicho.domain.models.analysis import OutcomeStatus
from bicho.domain.models.diff import NormalizedDiff
from bicho.domain.models.finding import Severity, SourceKind
from bicho.domain.ports.system import ProcessResult
from bicho.infrastructure.fs.workspace import TempWorkspaceFactory
from bicho.infrastructure.language.generic import GenericAdapter
from bicho.infrastructure.process.fake import FakeSubprocessRunner
from bicho.infrastructure.scanners.semgrep_runner import SemgrepScanner

_FINDINGS = (
    b'{"results": [{"check_id": "python-eval-on-input", "path": "./app/db.py", '
    b'"start": {"line": 11}, "end": {"line": 12}, '
    b'"extra": {"message": "eval is dangerous", "severity": "ERROR"}}]}'
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


def _scanner(result: ProcessResult) -> SemgrepScanner:
    return SemgrepScanner(
        runner=FakeSubprocessRunner(result), workspace=TempWorkspaceFactory(), ids=_Ids()
    )


async def test_no_files_is_zero_findings_without_running() -> None:
    runner = FakeSubprocessRunner(_process())
    scanner = SemgrepScanner(runner=runner, workspace=TempWorkspaceFactory(), ids=_Ids())

    outcome = await scanner.analyze(_context({}))

    assert outcome.status is OutcomeStatus.ZERO_FINDINGS
    assert runner.commands == []


async def test_maps_results_to_findings() -> None:
    outcome = await _scanner(_process(stdout=_FINDINGS)).analyze(
        _context({"app/db.py": "eval(x)\n"})
    )

    assert outcome.status is OutcomeStatus.OK
    assert len(outcome.findings) == 1
    finding = outcome.findings[0]
    assert finding.path == "app/db.py"
    assert finding.source_kind is SourceKind.SEMGREP
    assert finding.severity is Severity.HIGH
    assert finding.subcategory == "python-eval-on-input"
    assert finding.start_line == 11
    assert finding.end_line == 12


async def test_empty_results_is_zero_findings() -> None:
    outcome = await _scanner(_process(stdout=b'{"results": []}')).analyze(
        _context({"app/db.py": "x = 1\n"})
    )

    assert outcome.status is OutcomeStatus.ZERO_FINDINGS


async def test_timeout_degrades() -> None:
    outcome = await _scanner(_process(timed_out=True, returncode=None)).analyze(
        _context({"app/db.py": "x\n"})
    )

    assert outcome.status is OutcomeStatus.TIMEOUT
    assert outcome.degraded


async def test_nonzero_exit_degrades_with_stderr() -> None:
    outcome = await _scanner(_process(returncode=2, stderr=b"rule syntax error")).analyze(
        _context({"app/db.py": "x\n"})
    )

    assert outcome.status is OutcomeStatus.ERROR
    assert outcome.diagnostics[0].message == "rule syntax error"


async def test_unparseable_output_degrades() -> None:
    outcome = await _scanner(_process(stdout=b"not json at all")).analyze(
        _context({"app/db.py": "x\n"})
    )

    assert outcome.status is OutcomeStatus.ERROR
