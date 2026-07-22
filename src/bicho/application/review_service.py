"""The single review use case, shared by the manual endpoint and the webhook.

Both paths call ``run``; the only per-path difference is the ``ReviewOptions`` (dry_run/force/focus/
categories) and the trigger recorded on the request. There is no duplicated orchestration.
"""

from collections.abc import Mapping
from typing import Any

from bicho.application.analyzers.base import Analyzer
from bicho.application.context import ReviewContext
from bicho.application.graph.builder import run_graph
from bicho.application.graph.state import ReviewState
from bicho.domain.models.review import ReviewOptions, ReviewRequest, ReviewResult, ReviewStatus
from bicho.domain.ports.diff_parser import DiffParserPort
from bicho.domain.ports.github import GitHubPort
from bicho.domain.ports.language_adapter import LanguageAdapterRegistry
from bicho.domain.ports.system import IdGenerator


class ReviewService:
    """Runs the review graph for a pull request and returns a typed result."""

    def __init__(
        self,
        *,
        graph: Any,
        github: GitHubPort,
        diff_parser: DiffParserPort,
        adapters: LanguageAdapterRegistry,
        analyzers: Mapping[str, Analyzer],
        ids: IdGenerator,
    ) -> None:
        self._graph = graph
        self._github = github
        self._diff_parser = diff_parser
        self._adapters = adapters
        self._analyzers = analyzers
        self._ids = ids

    async def run(self, request: ReviewRequest, options: ReviewOptions) -> ReviewResult:
        """Run the full review pipeline: analyze, compose, and (unless dry-run) publish."""
        context = ReviewContext(
            github=self._github,
            diff_parser=self._diff_parser,
            adapters=self._adapters,
            analyzers=self._analyzers,
            options=options,
            correlation_id=self._ids.new_id(),
        )
        initial: ReviewState = {"request": request, "outcomes": []}
        final = await run_graph(self._graph, initial, context)
        findings = final.get("findings", [])
        confirmed = sum(1 for finding in findings if finding.is_confirmed)
        return ReviewResult(
            status=final.get("decision", ReviewStatus.DRY_RUN),
            draft=final.get("review_draft"),
            confirmed_count=confirmed,
            total_count=len(findings),
            review_id=final.get("published_review_id"),
        )
