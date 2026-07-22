"""Normalized diff model.

A ``NormalizedDiff`` is what anchoring works against: per-file hunks whose every line carries its
old-file and/or new-file line number, so we can decide whether a given ``(path, line, side)`` is
commentable on the PR. It is produced from GitHub's per-file ``patch`` hunks by the diff parser.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class FileChangeKind(StrEnum):
    """How a file changed in the PR."""

    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"
    RENAMED = "renamed"


class DiffLineKind(StrEnum):
    """The role of a single line within a hunk."""

    CONTEXT = "context"
    ADDED = "added"
    REMOVED = "removed"


class DiffLine(BaseModel):
    """One line of a hunk, with its old- and/or new-file line number."""

    model_config = ConfigDict(frozen=True)

    kind: DiffLineKind
    content: str
    old_line: int | None = None
    new_line: int | None = None


class DiffHunk(BaseModel):
    """A single ``@@`` hunk."""

    model_config = ConfigDict(frozen=True)

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    section_heading: str = ""
    lines: tuple[DiffLine, ...] = ()


class FileDiff(BaseModel):
    """The change to a single file, with its parsed hunks."""

    model_config = ConfigDict(frozen=True)

    path: str
    change_kind: FileChangeKind
    previous_path: str | None = None
    is_binary: bool = False
    hunks: tuple[DiffHunk, ...] = ()


class NormalizedDiff(BaseModel):
    """The full set of file changes in a PR."""

    model_config = ConfigDict(frozen=True)

    files: tuple[FileDiff, ...] = ()

    def file(self, path: str) -> FileDiff | None:
        """Return the :class:`FileDiff` for ``path``, or ``None`` if the path is not in the diff."""
        for file in self.files:
            if file.path == path:
                return file
        return None
