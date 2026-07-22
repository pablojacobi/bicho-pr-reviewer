"""Port for language-specific behaviour, keeping the review core language-agnostic."""

from collections.abc import Sequence
from typing import Protocol

from bicho.domain.models.pull_request import ChangedFile


class LanguageAdapter(Protocol):
    """Language-specific hooks that keep the core language-agnostic.

    - ``language``: the adapter's language name.
    - ``score``: how strongly the adapter applies to the changed files (0.0 = not at all).
    - ``in_scope``: whether a file is one this adapter analyzes.
    - ``default_analyzers``: analyzer names to run for this language.
    - ``enclosing_symbol``: the function/class enclosing a line, for stable fingerprints.
    """

    language: str

    def score(self, files: Sequence[ChangedFile]) -> float: ...
    def in_scope(self, file: ChangedFile) -> bool: ...
    def default_analyzers(self) -> tuple[str, ...]: ...
    def enclosing_symbol(self, path: str, content: str, line: int) -> str | None: ...


class LanguageAdapterRegistry(Protocol):
    """Selects the best-fitting :class:`LanguageAdapter` for a set of changed files."""

    def select(self, files: Sequence[ChangedFile]) -> LanguageAdapter: ...
