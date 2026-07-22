"""Selects the best-fitting language adapter, falling back to a generic one."""

from collections.abc import Sequence

from bicho.domain.models.pull_request import ChangedFile
from bicho.domain.ports.language_adapter import LanguageAdapter


class AdapterRegistry:
    """Holds candidate adapters plus a fallback, and picks the highest-scoring adapter."""

    def __init__(self, adapters: Sequence[LanguageAdapter], *, fallback: LanguageAdapter) -> None:
        self._adapters = tuple(adapters)
        self._fallback = fallback

    def select(self, files: Sequence[ChangedFile]) -> LanguageAdapter:
        best: LanguageAdapter | None = None
        best_score = 0.0
        for adapter in self._adapters:
            score = adapter.score(files)
            if score > best_score:
                best_score = score
                best = adapter
        return best if best is not None else self._fallback
