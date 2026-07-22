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
    detect_language,
    fetch_changed_files,
    fetch_pull_request,
    make_analyzer_node,
    normalize_diff,
    route_analyzers,
    select_analyzers,
)
from bicho.application.graph.state import ReviewState


def build_graph(analyzer_names: Sequence[str]):
    """Compile the review graph with one fan-out node per analyzer name."""
    builder = StateGraph(ReviewState, context_schema=ReviewContext)
    builder.add_node("fetch_pull_request", fetch_pull_request)
    builder.add_node("fetch_changed_files", fetch_changed_files)
    builder.add_node("normalize_diff", normalize_diff)
    builder.add_node("detect_language", detect_language)
    builder.add_node("select_analyzers", select_analyzers)
    for name in analyzer_names:
        builder.add_node(name, make_analyzer_node(name))
    builder.add_node("collect_findings", collect_findings)

    builder.add_edge(START, "fetch_pull_request")
    builder.add_edge("fetch_pull_request", "fetch_changed_files")
    builder.add_edge("fetch_changed_files", "normalize_diff")
    builder.add_edge("normalize_diff", "detect_language")
    builder.add_edge("detect_language", "select_analyzers")
    builder.add_conditional_edges(
        "select_analyzers", route_analyzers, [*analyzer_names, "collect_findings"]
    )
    for name in analyzer_names:
        builder.add_edge(name, "collect_findings")
    builder.add_edge("collect_findings", END)
    return builder.compile()


async def run_graph(graph: Any, initial: ReviewState, context: ReviewContext) -> ReviewState:
    """Invoke a compiled review graph and return the final typed state.

    ``graph`` is typed ``Any`` to encapsulate LangGraph's ``ainvoke`` overloads (a broad return
    union) at this one boundary; the rest of the codebase works with the typed state.
    """
    result = await graph.ainvoke(initial, context=context)
    return cast(ReviewState, result)
