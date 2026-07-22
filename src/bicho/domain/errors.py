"""Domain-level exceptions.

A small hierarchy rooted at :class:`BichoError` so callers can catch the domain's own failures
without resorting to broad ``except Exception`` handling.
"""


class BichoError(Exception):
    """Base class for all Bicho domain errors."""


class UnsafePathError(BichoError):
    """Raised when a repository-supplied path is unsafe to materialize (traversal/absolute)."""

    def __init__(self, path: str) -> None:
        super().__init__(f"unsafe path rejected: {path!r}")
        self.path = path
