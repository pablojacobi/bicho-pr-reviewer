"""The per-run review context injected into every graph node (LangGraph ``context_schema``).

Holds the ports and options a review needs, kept out of the graph *state* (which is pure data) so
nodes read dependencies via ``runtime.context`` rather than through globals.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from bicho.application.analyzers.base import Analyzer
from bicho.application.verifier import FindingVerifier
from bicho.domain.models.review import ReviewOptions
from bicho.domain.ports.diff_parser import DiffParserPort
from bicho.domain.ports.github import GitHubPort
from bicho.domain.ports.language_adapter import LanguageAdapterRegistry


@dataclass(frozen=True)
class ReviewContext:
    """Dependencies and options for a single review run."""

    github: GitHubPort
    diff_parser: DiffParserPort
    adapters: LanguageAdapterRegistry
    analyzers: Mapping[str, Analyzer]
    verifier: FindingVerifier
    options: ReviewOptions
    correlation_id: str
