"""The pip-audit dependency scanner.

Audits changed ``requirements*.txt`` manifests for known-vulnerable pinned dependencies, anchoring
each finding to the line pinning the package. Each manifest is written to an isolated workspace and
audited with ``--no-deps`` (only what the file pins, no resolution or install). pip-audit queries a
vulnerability database over the network, so this scanner is optional and every failure — timeout,
error, unparseable output — degrades to a diagnostic rather than raising.
"""

import re
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
from bicho.infrastructure.scanners.pip_audit_output import (
    PipAuditDependency,
    PipAuditOutput,
    PipAuditVuln,
)

_SOURCE = "pip-audit"
_OK_RETURN_CODES = (0, 1)  # 0 = no vulns, 1 = vulnerabilities found; both ran successfully.
_NAME_BOUNDARY = re.compile(r"[\s=<>!~;\[]")


def _is_manifest(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return name.startswith("requirements") and name.endswith(".txt")


def _line_of(content: str, package: str) -> int:
    for index, line in enumerate(content.splitlines(), start=1):
        name = _NAME_BOUNDARY.split(line.strip(), maxsplit=1)[0].lower()
        if name == package.lower():
            return index
    return 1


class DependencyAuditScanner:
    """Audits changed requirements manifests and returns normalized findings (never raises)."""

    def __init__(
        self,
        *,
        runner: SubprocessRunner,
        workspace: TempWorkspace,
        ids: IdGenerator,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._runner = runner
        self._workspace = workspace
        self._ids = ids
        self._timeout_seconds = timeout_seconds

    async def analyze(self, context: AnalysisContext) -> AnalyzerOutcome:
        manifests = {
            path: content for path, content in context.file_contents.items() if _is_manifest(path)
        }
        if not manifests:
            return AnalyzerOutcome(source=_SOURCE, status=OutcomeStatus.ZERO_FINDINGS)
        findings: list[Finding] = []
        diagnostics: list[Diagnostic] = []
        with self._workspace.create() as root:
            for path, content in manifests.items():
                target = resolve_within(root, path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                result = await self._runner.run(
                    self._command(target), timeout_seconds=self._timeout_seconds, cwd=root
                )
                self._consume(result, path, content, context, findings, diagnostics)
        return self._outcome(findings, diagnostics)

    def _command(self, manifest: Path) -> list[str]:
        return [
            "pip-audit",
            "--requirement",
            str(manifest),
            "--format",
            "json",
            "--no-deps",
            "--progress-spinner",
            "off",
        ]

    def _consume(
        self,
        result: ProcessResult,
        path: str,
        content: str,
        context: AnalysisContext,
        findings: list[Finding],
        diagnostics: list[Diagnostic],
    ) -> None:
        if result.timed_out:
            diagnostics.append(
                self._diagnostic(OutcomeStatus.TIMEOUT, f"pip-audit timed out on {path}")
            )
            return
        if result.returncode not in _OK_RETURN_CODES:
            detail = result.stderr.decode("utf-8", "replace").strip()
            diagnostics.append(
                self._diagnostic(OutcomeStatus.ERROR, detail or f"pip-audit failed on {path}")
            )
            return
        try:
            output = PipAuditOutput.model_validate_json(result.stdout)
        except ValueError:
            diagnostics.append(
                self._diagnostic(
                    OutcomeStatus.ERROR, f"could not parse pip-audit output for {path}"
                )
            )
            return
        for dependency in output.dependencies:
            line = _line_of(content, dependency.name)
            findings.extend(
                self._to_finding(dependency, vuln, path, line, context) for vuln in dependency.vulns
            )

    def _diagnostic(self, status: OutcomeStatus, message: str) -> Diagnostic:
        return Diagnostic(source=_SOURCE, status=status, message=message)

    def _to_finding(
        self,
        dependency: PipAuditDependency,
        vuln: PipAuditVuln,
        path: str,
        line: int,
        context: AnalysisContext,
    ) -> Finding:
        fix = ", ".join(vuln.fix_versions)
        recommendation = (
            f"Upgrade {dependency.name} to {fix}."
            if fix
            else f"Upgrade {dependency.name} to a patched version."
        )
        return Finding(
            id=self._ids.new_id(),
            fingerprint=compute_fingerprint(
                path=path,
                category=Category.DEPENDENCY.value,
                subcategory=vuln.id,
                rule_key=vuln.id,
                enclosing_symbol=None,
                snippet=dependency.name,
            ),
            category=Category.DEPENDENCY,
            subcategory=vuln.id,
            severity=Severity.HIGH,
            confidence=Confidence.HIGH,
            title=f"{dependency.name} {dependency.version}: {vuln.id}",
            explanation=vuln.description
            or f"{dependency.name} {dependency.version} has a known vulnerability ({vuln.id}).",
            impact="A dependency pinned by this change has a known vulnerability.",
            recommendation=recommendation,
            path=path,
            start_line=line,
            end_line=line,
            diff_side=DiffSide.RIGHT,
            source_kind=SourceKind.PIP_AUDIT,
            source_name=_SOURCE,
            head_sha=context.head_sha,
            language=context.language,
            framework=context.framework,
        )

    def _outcome(self, findings: list[Finding], diagnostics: list[Diagnostic]) -> AnalyzerOutcome:
        if findings:
            status = OutcomeStatus.OK
        elif diagnostics:
            status = diagnostics[0].status
        else:
            status = OutcomeStatus.ZERO_FINDINGS
        return AnalyzerOutcome(
            source=_SOURCE,
            status=status,
            findings=tuple(findings),
            diagnostics=tuple(diagnostics),
        )


def build_dependency_audit_scanner(
    *,
    runner: SubprocessRunner,
    workspace: TempWorkspace,
    ids: IdGenerator,
    timeout_seconds: float = 60.0,
) -> DependencyAuditScanner:
    """Construct the pip-audit dependency scanner."""
    return DependencyAuditScanner(
        runner=runner, workspace=workspace, ids=ids, timeout_seconds=timeout_seconds
    )
