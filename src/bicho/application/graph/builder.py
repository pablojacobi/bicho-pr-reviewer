"""Build the review ``StateGraph``.

Linear spine (fetch → normalize → detect → select), then a parallel fan-out over the selected
analyzers, fanned back in at ``collect_findings``. No checkpointer, no interrupts, no persistence.
"""
# LangGraph's StateGraph builder methods are partially-unknown-typed, and their node-callable
# overloads don't recognize our node alias; this file is pure graph glue, so relax those two checks.
# pyright: reportUnknownMemberType=false, reportArgumentType=false

from collections.abc import Sequence
from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from bicho.application.context import ReviewContext
from bicho.application.graph.nodes import (
    collect_findings,
    compose_review,
    detect_language,
    fetch_changed_files,
    fetch_pull_request,
    gather_file_contents,
    idempotency_guard,
    make_analyzer_node,
    normalize_diff,
    publish_github_review,
    route_after_idempotency,
    route_after_stale,
    route_analyzers,
    select_analyzers,
    stale_head_guard,
    verify_findings,
)
from bicho.application.graph.state import ReviewState


def build_graph(analyzer_names: Sequence[str]):
    """Compile the review graph with one fan-out node per analyzer name."""
    builder = StateGraph(ReviewState, context_schema=ReviewContext)
    builder.add_node("fetch_pull_request", fetch_pull_request)
    builder.add_node("fetch_changed_files", fetch_changed_files)
    builder.add_node("normalize_diff", normalize_diff)
    builder.add_node("detect_language", detect_language)
    builder.add_node("gather_file_contents", gather_file_contents)
    builder.add_node("select_analyzers", select_analyzers)
    for name in analyzer_names:
        builder.add_node(name, make_analyzer_node(name))
    builder.add_node("collect_findings", collect_findings)
    builder.add_node("verify_findings", verify_findings)
    builder.add_node("compose_review", compose_review)
    builder.add_node("idempotency_guard", idempotency_guard)
    builder.add_node("stale_head_guard", stale_head_guard)
    builder.add_node("publish_github_review", publish_github_review)

    builder.add_edge(START, "fetch_pull_request")
    builder.add_edge("fetch_pull_request", "fetch_changed_files")
    builder.add_edge("fetch_changed_files", "normalize_diff")
    builder.add_edge("normalize_diff", "detect_language")
    builder.add_edge("detect_language", "gather_file_contents")
    builder.add_edge("gather_file_contents", "select_analyzers")
    builder.add_conditional_edges(
        "select_analyzers", route_analyzers, [*analyzer_names, "collect_findings"]
    )
    for name in analyzer_names:
        builder.add_edge(name, "collect_findings")
    builder.add_edge("collect_findings", "verify_findings")
    builder.add_edge("verify_findings", "compose_review")
    builder.add_edge("compose_review", "idempotency_guard")
    builder.add_conditional_edges(
        "idempotency_guard", route_after_idempotency, ["stale_head_guard", END]
    )
    builder.add_conditional_edges(
        "stale_head_guard", route_after_stale, ["publish_github_review", END]
    )
    builder.add_edge("publish_github_review", END)
    return builder.compile()


async def run_graph(graph: Any, initial: ReviewState, context: ReviewContext) -> ReviewState:
    """Invoke a compiled review graph and return the final typed state.

    ``graph`` is typed ``Any`` to encapsulate LangGraph's ``ainvoke`` overloads (a broad return
    union) at this one boundary; the rest of the codebase works with the typed state.
    """
    result = await graph.ainvoke(initial, context=context)
    return cast(ReviewState, result)
