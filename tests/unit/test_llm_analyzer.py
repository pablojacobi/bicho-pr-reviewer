"""Tests for the LLM analyzer base and the correctness analyzer."""

from collections.abc import Mapping

from bicho.application.analyzers.base import AnalysisContext
from bicho.application.analyzers.correctness import build_correctness_analyzer
from bicho.application.analyzers.schemas import AnalyzerReport, RawFinding
from bicho.domain.models.analysis import OutcomeStatus
from bicho.domain.models.diff import NormalizedDiff
from bicho.domain.models.finding import Category, Confidence, Severity, SourceKind
from bicho.domain.ports.model_provider import ok_result
from bicho.infrastructure.language.generic import GenericAdapter
from bicho.infrastructure.model.fake import FakeModelProvider

_EMPTY: Mapping[str, str] = {}


class _Ids:
    def __init__(self) -> None:
        self._n = 0

    def new_id(self) -> str:
        self._n += 1
        return f"id-{self._n}"


def _raw(start: int = 11, end: int = 12) -> RawFinding:
    return RawFinding(
        title="Off-by-one",
        explanation="e",
        impact="i",
        recommendation="r",
        path="app/db.py",
        start_line=start,
        end_line=end,
        severity=Severity.HIGH,
        confidence=Confidence.MEDIUM,
        subcategory="off-by-one",
        snippet="x",
    )


def _context(
    diff: NormalizedDiff, *, file_contents: Mapping[str, str] | None = None
) -> AnalysisContext:
    return AnalysisContext(
        diff=diff,
        head_sha="sha",
        language="python",
        framework=None,
        correlation_id="c",
        adapter=GenericAdapter(),
        file_contents=file_contents if file_contents is not None else _EMPTY,
    )


async def test_analyzer_normalizes_findings(sample_diff: NormalizedDiff) -> None:
    model = FakeModelProvider([ok_result(AnalyzerReport(findings=(_raw(),)), model_id="fake")])
    analyzer = build_correctness_analyzer(model=model, ids=_Ids())

    outcome = await analyzer.analyze(_context(sample_diff))

    assert outcome.status is OutcomeStatus.OK
    (finding,) = outcome.findings
    assert finding.category is Category.CORRECTNESS
    assert finding.source_kind is SourceKind.LLM_ANALYZER
    assert finding.head_sha == "sha"
    assert finding.model_id == "fake"
    assert finding.id == "id-1"
    assert finding.fingerprint


async def test_analyzer_reports_zero_findings(sample_diff: NormalizedDiff) -> None:
    model = FakeModelProvider([ok_result(AnalyzerReport(), model_id="m")])
    analyzer = build_correctness_analyzer(model=model, ids=_Ids())

    outcome = await analyzer.analyze(_context(sample_diff))

    assert outcome.status is OutcomeStatus.ZERO_FINDINGS
    assert outcome.findings == ()


async def test_analyzer_degrades_on_model_error(sample_diff: NormalizedDiff) -> None:
    analyzer = build_correctness_analyzer(model=FakeModelProvider(), ids=_Ids())

    outcome = await analyzer.analyze(_context(sample_diff))

    assert outcome.status is OutcomeStatus.ERROR
    assert outcome.degraded is True
    assert len(outcome.diagnostics) == 1


async def test_analyzer_uses_file_content_for_enclosing_symbol(sample_diff: NormalizedDiff) -> None:
    model = FakeModelProvider([ok_result(AnalyzerReport(findings=(_raw(),)), model_id="m")])
    analyzer = build_correctness_analyzer(model=model, ids=_Ids())

    outcome = await analyzer.analyze(_context(sample_diff, file_contents={"app/db.py": "code"}))

    assert outcome.status is OutcomeStatus.OK


async def test_analyzer_clamps_inverted_line_range(sample_diff: NormalizedDiff) -> None:
    model = FakeModelProvider(
        [ok_result(AnalyzerReport(findings=(_raw(start=12, end=11),)), model_id="m")]
    )
    analyzer = build_correctness_analyzer(model=model, ids=_Ids())

    (finding,) = (await analyzer.analyze(_context(sample_diff))).findings

    assert finding.start_line == 12
    assert finding.end_line == 12
