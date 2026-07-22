"""The resilient node wrapper — analyzer/scanner nodes degrade instead of raising.

In LangGraph 1.x, if any branch of a parallel superstep raises, the whole superstep is rolled
back and the run errors. So every analyzer/scanner node is wrapped here: any exception becomes an
ERROR ``AnalyzerOutcome`` written to the ``outcomes`` reducer, and the superstep completes normally.
"""

from collections.abc import Awaitable, Callable

from langgraph.runtime import Runtime

from bicho.application.context import ReviewContext
from bicho.application.graph.state import ReviewState
from bicho.domain.models.analysis import AnalyzerOutcome, Diagnostic, OutcomeStatus

AnalyzerRun = Callable[[ReviewState, Runtime[ReviewContext]], Awaitable[AnalyzerOutcome]]
Node = Callable[[ReviewState, Runtime[ReviewContext]], Awaitable[dict[str, object]]]


def resilient_analyzer_node(name: str, run: AnalyzerRun) -> Node:
    """Wrap an analyzer run so any exception degrades to an ERROR outcome, never rolling back."""

    async def node(state: ReviewState, runtime: Runtime[ReviewContext]) -> dict[str, object]:
        try:
            outcome = await run(state, runtime)
        except Exception as exc:  # deliberately broad: degrade, never abort the parallel superstep
            outcome = AnalyzerOutcome(
                source=name,
                status=OutcomeStatus.ERROR,
                diagnostics=(
                    Diagnostic(source=name, status=OutcomeStatus.ERROR, message=str(exc)),
                ),
            )
        return {"outcomes": [outcome]}

    return node
