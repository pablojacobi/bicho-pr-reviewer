"""The Semgrep Community Edition scanner.

Materializes the in-scope changed files into an isolated temporary workspace at sanitized paths,
runs ``semgrep scan`` (no shell, hard timeout, no network/metrics), and normalizes the JSON output
into domain findings. Every failure mode — timeout, non-zero exit, unparseable output — becomes a
degraded ``AnalyzerOutcome`` rather than an exception, keeping the parallel superstep valid. The
repository is never cloned and its code is never executed; only static analysis runs.
"""

from pathlib import Path

from bicho.application.analyzers.base import AnalysisContext
from bicho.domain.models.analysis import AnalyzerOutcome, Diagnostic, OutcomeStatus
from bicho.domain.models.finding import (
    Category,
    Confidence,
    DiffSide,
    Finding,
    Severity,
    SourceKind,
)
from bicho.domain.ports.system import IdGenerator, ProcessResult, SubprocessRunner, TempWorkspace
from bicho.domain.services.fingerprint import compute_fingerprint
from bicho.infrastructure.fs.pathsafe import resolve_within
from bicho.infrastructure.scanners.semgrep_output import SemgrepOutput, SemgrepResult

_SOURCE = "semgrep"
_SEVERITY = {"ERROR": Severity.HIGH, "WARNING": Severity.MEDIUM, "INFO": Severity.LOW}


class SemgrepScanner:
    """Runs Semgrep over the changed files and returns normalized findings (never raises)."""

    def __init__(
        self,
        *,
        runner: SubprocessRunner,
        workspace: TempWorkspace,
        ids: IdGenerator,
        config: str = "resources/semgrep",
        timeout_seconds: float = 60.0,
    ) -> None:
        self._runner = runner
        self._workspace = workspace
        self._ids = ids
        self._config = config
        self._timeout_seconds = timeout_seconds

    async def analyze(self, context: AnalysisContext) -> AnalyzerOutcome:
        if not context.file_contents:
            return AnalyzerOutcome(source=_SOURCE, status=OutcomeStatus.ZERO_FINDINGS)
        with self._workspace.create() as root:
            for path, content in context.file_contents.items():
                target = resolve_within(root, path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            result = await self._runner.run(
                self._command(), timeout_seconds=self._timeout_seconds, cwd=root
            )
        return self._to_outcome(result, context)

    def _command(self) -> list[str]:
        return [
            "semgrep",
            "scan",
            "--config",
            str(Path(self._config).resolve()),
            "--json",
            "--quiet",
            "--disable-version-check",
            "--metrics=off",
            "--no-git-ignore",
            "--timeout",
            str(int(self._timeout_seconds)),
            ".",
        ]

    def _to_outcome(self, result: ProcessResult, context: AnalysisContext) -> AnalyzerOutcome:
        if result.timed_out:
            return self._degraded(OutcomeStatus.TIMEOUT, "semgrep timed out")
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", "replace").strip()
            return self._degraded(OutcomeStatus.ERROR, detail or "semgrep exited non-zero")
        try:
            output = SemgrepOutput.model_validate_json(result.stdout)
        except ValueError:
            return self._degraded(OutcomeStatus.ERROR, "could not parse semgrep JSON output")
        findings = tuple(self._to_finding(match, context) for match in output.results)
        status = OutcomeStatus.OK if findings else OutcomeStatus.ZERO_FINDINGS
        return AnalyzerOutcome(source=_SOURCE, status=status, findings=findings)

    def _degraded(self, status: OutcomeStatus, message: str) -> AnalyzerOutcome:
        return AnalyzerOutcome(
            source=_SOURCE,
            status=status,
            diagnostics=(Diagnostic(source=_SOURCE, status=status, message=message),),
        )

    def _to_finding(self, match: SemgrepResult, context: AnalysisContext) -> Finding:
        path = match.path.removeprefix("./")
        # Semgrep namespaces a rule id by the ruleset's file path (e.g.
        # "app.resources.semgrep.python.python-eval-on-input"); keep only the rule's own name.
        rule = match.check_id.rsplit(".", 1)[-1]
        start = match.start.line
        end = max(start, match.end.line)
        return Finding(
            id=self._ids.new_id(),
            fingerprint=compute_fingerprint(
                path=path,
                category=Category.SECURITY.value,
                subcategory=rule,
                rule_key=rule,
                enclosing_symbol=None,
                snippet="",
            ),
            category=Category.SECURITY,
            subcategory=rule,
            severity=_SEVERITY.get(match.extra.severity.upper(), Severity.LOW),
            confidence=Confidence.HIGH,
            title=f"Semgrep: {rule}",
            explanation=match.extra.message or "A Semgrep rule matched this code.",
            impact="A static-analysis rule flagged a pattern introduced by this change.",
            recommendation="Review the flagged pattern and remediate as the rule advises.",
            path=path,
            start_line=start,
            end_line=end,
            diff_side=DiffSide.RIGHT,
            source_kind=SourceKind.SEMGREP,
            source_name=_SOURCE,
            head_sha=context.head_sha,
            language=context.language,
            framework=context.framework,
        )


def build_semgrep_scanner(
    *,
    runner: SubprocessRunner,
    workspace: TempWorkspace,
    ids: IdGenerator,
    config: str = "resources/semgrep",
    timeout_seconds: float = 60.0,
) -> SemgrepScanner:
    """Construct the Semgrep scanner."""
    return SemgrepScanner(
        runner=runner,
        workspace=workspace,
        ids=ids,
        config=config,
        timeout_seconds=timeout_seconds,
    )
