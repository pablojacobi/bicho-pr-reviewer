"""Tests for the language adapter contract, generic fallback, and registry selection."""

from collections.abc import Sequence

from bicho.domain.models.pull_request import ChangedFile
from bicho.domain.ports.language_adapter import LanguageAdapter, LanguageAdapterRegistry
from bicho.infrastructure.language.generic import GenericAdapter
from bicho.infrastructure.language.registry import AdapterRegistry


class _StubAdapter:
    def __init__(self, language: str, score: float) -> None:
        self.language = language
        self._score = score

    def score(self, files: Sequence[ChangedFile]) -> float:
        return self._score

    def in_scope(self, file: ChangedFile) -> bool:
        return True

    def default_analyzers(self) -> tuple[str, ...]:
        return ("x",)

    def enclosing_symbol(self, path: str, content: str, line: int) -> str | None:
        return None


def _files() -> tuple[ChangedFile, ...]:
    return (ChangedFile(filename="a.py", status="modified", patch="@@ -1 +1 @@\n-a\n+b\n"),)


def test_generic_adapter_basics() -> None:
    adapter: LanguageAdapter = GenericAdapter()

    assert adapter.language == "generic"
    assert adapter.score(_files()) > 0
    assert adapter.score(()) == 0.0
    assert adapter.default_analyzers()
    assert adapter.enclosing_symbol("a.py", "code", 1) is None


def test_generic_adapter_in_scope_skips_binary_files() -> None:
    adapter = GenericAdapter()

    assert adapter.in_scope(ChangedFile(filename="a.py", status="modified", patch="x")) is True
    assert adapter.in_scope(ChangedFile(filename="img.png", status="added", patch=None)) is False


def test_registry_selects_the_highest_scoring_adapter() -> None:
    registry: LanguageAdapterRegistry = AdapterRegistry(
        [_StubAdapter("ruby", 0.3), _StubAdapter("python", 0.9)], fallback=GenericAdapter()
    )

    assert registry.select(_files()).language == "python"


def test_registry_falls_back_when_no_adapter_scores() -> None:
    registry = AdapterRegistry([_StubAdapter("python", 0.0)], fallback=GenericAdapter())

    assert registry.select(_files()).language == "generic"
