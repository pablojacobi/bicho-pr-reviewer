"""The base LLM analyzer: render a prompt, call the model, normalize findings.

A failed model call becomes a degraded ``AnalyzerOutcome`` (never an exception), so the graph's
parallel superstep is not rolled back. Invalid line ranges from the model are clamped, not dropped.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from bicho.application.analyzers.schemas import AnalyzerReport, RawFinding
from bicho.application.prompts.registry import PROMPT_VERSION, get_prompt
from bicho.domain.models.analysis import AnalyzerOutcome, Diagnostic, OutcomeStatus
from bicho.domain.models.diff import NormalizedDiff
from bicho.domain.models.finding import Category, DiffSide, Finding, SourceKind
from bicho.domain.ports.language_adapter import LanguageAdapter
from bicho.domain.ports.model_provider import ModelProvider, RunMeta
from bicho.domain.ports.system import IdGenerator
from bicho.domain.services.fingerprint import compute_fingerprint

_LINE_PREFIX = {"added": "+", "removed": "-", "context": " "}


@dataclass(frozen=True)
class AnalysisContext:
    """Everything an analyzer needs about the pull request under review."""

    diff: NormalizedDiff
    head_sha: str
    language: str
    framework: str | None
    correlation_id: str
    adapter: LanguageAdapter
    file_contents: Mapping[str, str]


class Analyzer(Protocol):
    """Runs one analyzer over the PR context and returns an outcome (never raises)."""

    async def analyze(self, context: AnalysisContext) -> AnalyzerOutcome: ...


def render_diff(diff: NormalizedDiff) -> str:
    """Render the diff as annotated text for an analyzer prompt."""
    blocks: list[str] = []
    for file in diff.files:
        lines = [f"### {file.path} ({file.change_kind.value})"]
        for hunk in file.hunks:
            lines.append(f"@@ {hunk.section_heading}".rstrip())
            for line in hunk.lines:
                number = line.new_line if line.new_line is not None else line.old_line
                lines.append(f"{number}\t{_LINE_PREFIX[line.kind.value]}{line.content}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


class LLMAnalyzer:
    """Runs one LLM analyzer role and normalizes its output into domain findings."""

    def __init__(
        self, *, role: str, category: Category, model: ModelProvider, ids: IdGenerator
    ) -> None:
        self._role = role
        self._category = category
        self._model = model
        self._ids = ids

    async def analyze(self, context: AnalysisContext) -> AnalyzerOutcome:
        prompt = f"{get_prompt(self._role)}\n\n## Diff\n{render_diff(context.diff)}\n"
        meta = RunMeta(
            role=self._role, prompt_version=PROMPT_VERSION, correlation_id=context.correlation_id
        )
        result = await self._model.structured(prompt=prompt, schema=AnalyzerReport, meta=meta)
        if not result.ok or result.value is None:
            message = result.error or "analyzer produced no result"
            return AnalyzerOutcome(
                source=self._role,
                status=OutcomeStatus.ERROR,
                diagnostics=(
                    Diagnostic(source=self._role, status=OutcomeStatus.ERROR, message=message),
                ),
            )
        findings = tuple(
            self._to_finding(raw, context, result.model_id) for raw in result.value.findings
        )
        status = OutcomeStatus.OK if findings else OutcomeStatus.ZERO_FINDINGS
        return AnalyzerOutcome(source=self._role, status=status, findings=findings)

    def _to_finding(self, raw: RawFinding, context: AnalysisContext, model_id: str) -> Finding:
        content = context.file_contents.get(raw.path)
        symbol = (
            context.adapter.enclosing_symbol(raw.path, content, raw.start_line)
            if content is not None
            else None
        )
        return Finding(
            id=self._ids.new_id(),
            fingerprint=compute_fingerprint(
                path=raw.path,
                category=self._category.value,
                subcategory=raw.subcategory,
                rule_key=raw.subcategory,
                enclosing_symbol=symbol,
                snippet=raw.snippet,
            ),
            category=self._category,
            subcategory=raw.subcategory,
            severity=raw.severity,
            confidence=raw.confidence,
            title=raw.title,
            explanation=raw.explanation,
            impact=raw.impact,
            recommendation=raw.recommendation,
            path=raw.path,
            start_line=raw.start_line,
            end_line=max(raw.start_line, raw.end_line),
            diff_side=DiffSide.RIGHT,
            snippet=raw.snippet,
            source_kind=SourceKind.LLM_ANALYZER,
            source_name=self._role,
            head_sha=context.head_sha,
            prompt_version=PROMPT_VERSION,
            model_id=model_id,
            language=context.language,
            framework=context.framework,
        )
