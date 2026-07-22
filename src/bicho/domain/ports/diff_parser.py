"""Port for parsing unified-diff hunks into the domain model."""

from typing import Protocol

from bicho.domain.models.diff import DiffHunk


class DiffParserPort(Protocol):
    """Parses a single file's unified-diff ``patch`` (a sequence of ``@@`` hunks) into hunks."""

    def parse_hunks(self, patch: str) -> tuple[DiffHunk, ...]: ...
