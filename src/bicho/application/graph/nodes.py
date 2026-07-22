"""LangGraph node functions for the review workflow."""

from langgraph.runtime import Runtime

from bicho.application.analyzers.base import AnalysisContext
from bicho.application.context import ReviewContext
from bicho.application.graph.resilience import Node, resilient_analyzer_node
from bicho.application.graph.state import ReviewState
from bicho.domain.models.analysis import AnalyzerOutcome
from bicho.domain.models.diff import FileChangeKind, FileDiff, NormalizedDiff
from bicho.domain.models.pull_request import ChangedFile
from bicho.domain.ports.diff_parser import DiffParserPort
from bicho.domain.services.dedup import deduplicate

_CHANGE_KIND = {
    "added": FileChangeKind.ADDED,
    "removed": FileChangeKind.REMOVED,
    "renamed": FileChangeKind.RENAMED,
}


async def fetch_pull_request(
    state: ReviewState, runtime: Runtime[ReviewContext]
) -> dict[str, object]:
    request = state["request"]
    pull_request = await runtime.context.github.fetch_pull_request(
        request.repository, request.pr_number
    )
    return {"pull_request": pull_request}


async def fetch_changed_files(
    state: ReviewState, runtime: Runtime[ReviewContext]
) -> dict[str, object]:
    request = state["request"]
    files = await runtime.context.github.fetch_changed_files(request.repository, request.pr_number)
    return {"changed_files": files}


def normalize_diff(state: ReviewState, runtime: Runtime[ReviewContext]) -> dict[str, object]:
    parser = runtime.context.diff_parser
    files = tuple(_to_file_diff(changed, parser) for changed in state["changed_files"])
    return {"diff": NormalizedDiff(files=files)}


def detect_language(state: ReviewState, runtime: Runtime[ReviewContext]) -> dict[str, object]:
    adapter = runtime.context.adapters.select(state["changed_files"])
    return {"adapter": adapter, "language": adapter.language}


def select_analyzers(state: ReviewState, runtime: Runtime[ReviewContext]) -> dict[str, object]:
    available = set(runtime.context.analyzers)
    selected = [name for name in state["adapter"].default_analyzers() if name in available]
    return {"selected": selected}


def collect_findings(state: ReviewState, runtime: Runtime[ReviewContext]) -> dict[str, object]:
    findings = [finding for outcome in state["outcomes"] for finding in outcome.findings]
    return {"findings": deduplicate(findings)}


def route_analyzers(state: ReviewState) -> list[str]:
    selected = state.get("selected") or []
    return selected if selected else ["collect_findings"]


def make_analyzer_node(name: str) -> Node:
    async def run(state: ReviewState, runtime: Runtime[ReviewContext]) -> AnalyzerOutcome:
        context = runtime.context
        analysis = AnalysisContext(
            diff=state["diff"],
            head_sha=state["pull_request"].head_sha,
            language=state["language"],
            framework=None,
            correlation_id=context.correlation_id,
            adapter=state["adapter"],
            file_contents={},
        )
        return await context.analyzers[name].analyze(analysis)

    return resilient_analyzer_node(name, run)


def _to_file_diff(changed: ChangedFile, parser: DiffParserPort) -> FileDiff:
    return FileDiff(
        path=changed.filename,
        change_kind=_CHANGE_KIND.get(changed.status, FileChangeKind.MODIFIED),
        previous_path=changed.previous_filename,
        is_binary=changed.patch is None,
        hunks=parser.parse_hunks(changed.patch or ""),
    )
