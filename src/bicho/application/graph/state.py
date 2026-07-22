"""The typed graph state.

Only the reducer-backed key (``outcomes``) may be written by parallel analyzer nodes; every other
key is written by a single node on the spine. This is what keeps the parallel superstep valid.
"""

import operator
from typing import Annotated, NotRequired, TypedDict

from bicho.domain.models.analysis import AnalyzerOutcome
from bicho.domain.models.diff import NormalizedDiff
from bicho.domain.models.finding import Finding
from bicho.domain.models.pull_request import ChangedFile, PullRequest
from bicho.domain.models.review import ReviewDraft, ReviewRequest
from bicho.domain.ports.language_adapter import LanguageAdapter


class ReviewState(TypedDict):
    """The state threaded through the review graph."""

    request: ReviewRequest
    # The only key parallel (analyzer) nodes write — accumulated via list concatenation.
    outcomes: Annotated[list[AnalyzerOutcome], operator.add]
    # Single-writer keys, populated by the linear spine.
    pull_request: NotRequired[PullRequest]
    changed_files: NotRequired[tuple[ChangedFile, ...]]
    diff: NotRequired[NormalizedDiff]
    language: NotRequired[str]
    adapter: NotRequired[LanguageAdapter]
    selected: NotRequired[list[str]]
    findings: NotRequired[list[Finding]]
    review_draft: NotRequired[ReviewDraft]
