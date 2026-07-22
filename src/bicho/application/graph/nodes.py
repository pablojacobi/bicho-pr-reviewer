"""LangGraph node functions for the review workflow."""

from langgraph.graph import END
from langgraph.runtime import Runtime

from bicho.application.analyzers.base import AnalysisContext
from bicho.application.context import ReviewContext
from bicho.application.graph.compose import WORKFLOW_VERSION, compose_review_draft
from bicho.application.graph.resilience import Node, resilient_analyzer_node
from bicho.application.graph.state import ReviewState
from bicho.domain.models.analysis import AnalyzerOutcome
from bicho.domain.models.diff import FileChangeKind, FileDiff, NormalizedDiff
from bicho.domain.models.marker import ReviewMarker
from bicho.domain.models.pull_request import ChangedFile
from bicho.domain.models.review import ReviewStatus
from bicho.domain.ports.diff_parser import DiffParserPort
from bicho.domain.services.dedup import deduplicate
from bicho.domain.services.verification_policy import verify

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


def verify_findings(state: ReviewState, runtime: Runtime[ReviewContext]) -> dict[str, object]:
    verified = [verify(finding) for finding in state.get("findings", [])]
    return {"findings": verified}


def compose_review(state: ReviewState, runtime: Runtime[ReviewContext]) -> dict[str, object]:
    draft = compose_review_draft(
        findings=state.get("findings", []),
        diff=state["diff"],
        pull_request=state["pull_request"],
        outcomes=state["outcomes"],
    )
    return {"review_draft": draft}


async def idempotency_guard(
    state: ReviewState, runtime: Runtime[ReviewContext]
) -> dict[str, object]:
    """Decide whether to publish. Short-circuits a dry run, and skips an already-reviewed head.

    A decision is set only for the terminal outcomes (dry run, already reviewed); leaving it unset
    means "proceed to the stale-head guard, then publish".
    """
    options = runtime.context.options
    if options.dry_run:
        return {"decision": ReviewStatus.DRY_RUN}
    if options.force:
        return {}
    pull_request = state["pull_request"]
    reviews = await runtime.context.github.list_reviews(
        pull_request.repository, pull_request.number
    )
    for review in reviews:
        marker = ReviewMarker.parse(review.body)
        if (
            marker is not None
            and marker.head_sha == pull_request.head_sha
            and marker.workflow_version == WORKFLOW_VERSION
        ):
            return {"decision": ReviewStatus.SKIPPED}
    return {}


async def stale_head_guard(
    state: ReviewState, runtime: Runtime[ReviewContext]
) -> dict[str, object]:
    """Re-fetch the head SHA just before publishing and abort if the PR moved under us."""
    analyzed = state["pull_request"]
    current = await runtime.context.github.fetch_pull_request(analyzed.repository, analyzed.number)
    if current.head_sha != analyzed.head_sha:
        return {"decision": ReviewStatus.STALE}
    return {}


async def publish_github_review(
    state: ReviewState, runtime: Runtime[ReviewContext]
) -> dict[str, object]:
    """Publish the composed review as one GitHub review and record its id."""
    pull_request = state["pull_request"]
    review_id = await runtime.context.github.publish_review(
        pull_request.repository, pull_request.number, state["review_draft"]
    )
    return {"decision": ReviewStatus.COMPLETED, "published_review_id": review_id}


def route_after_idempotency(state: ReviewState) -> str:
    """Proceed to the stale-head guard unless a terminal decision was already made."""
    return END if state.get("decision") is not None else "stale_head_guard"


def route_after_stale(state: ReviewState) -> str:
    """Publish unless the head went stale."""
    return END if state.get("decision") is ReviewStatus.STALE else "publish_github_review"


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
