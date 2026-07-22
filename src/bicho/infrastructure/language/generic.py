"""A language-agnostic fallback adapter.

Used when no language-specific adapter fits, so unknown languages degrade to generic analysis rather
than failing. It provides no symbol extraction (fingerprints fall back to path + code shape).
"""

from collections.abc import Sequence

from bicho.domain.models.pull_request import ChangedFile

_CORE_ANALYZERS = (
    "correctness",
    "security",
    "performance",
    "maintainability",
    "tests",
    "contracts",
)


class GenericAdapter:
    """A minimal :class:`LanguageAdapter` used as the fallback."""

    language = "generic"

    def score(self, files: Sequence[ChangedFile]) -> float:
        return 0.1 if files else 0.0

    def in_scope(self, file: ChangedFile) -> bool:
        return file.patch is not None

    def default_analyzers(self) -> tuple[str, ...]:
        return _CORE_ANALYZERS

    def enclosing_symbol(self, path: str, content: str, line: int) -> str | None:
        return None
