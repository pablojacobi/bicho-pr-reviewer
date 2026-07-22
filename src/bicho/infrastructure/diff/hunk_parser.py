"""A small, dependency-free unified-diff hunk parser.

This replaces a third-party diff library (see the plan / ADR): it parses the per-file ``patch`` text
GitHub returns from the "list pull request files" endpoint into :class:`DiffHunk` objects, tracking
each line's old- and new-file number so inline comments can be anchored precisely.
"""

import re

from bicho.domain.models.diff import DiffHunk, DiffLine, DiffLineKind

_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: ?(.*))?$")


class DiffParser:
    """Parses unified-diff hunks (the ``DiffParserPort`` implementation)."""

    def parse_hunks(self, patch: str) -> tuple[DiffHunk, ...]:
        hunks: list[DiffHunk] = []
        header: re.Match[str] | None = None
        lines: list[DiffLine] = []
        old_line = 0
        new_line = 0

        for raw in patch.splitlines():
            match = _HUNK_HEADER.match(raw)
            if match is not None:
                if header is not None:
                    hunks.append(_build_hunk(header, lines))
                header = match
                old_line = int(match.group(1))
                new_line = int(match.group(3))
                lines = []
                continue
            if header is None:
                continue  # defensive: any preamble before the first hunk is ignored
            if raw.startswith("\\"):
                continue  # "\ No newline at end of file"
            if raw.startswith("+"):
                lines.append(DiffLine(kind=DiffLineKind.ADDED, content=raw[1:], new_line=new_line))
                new_line += 1
            elif raw.startswith("-"):
                lines.append(
                    DiffLine(kind=DiffLineKind.REMOVED, content=raw[1:], old_line=old_line)
                )
                old_line += 1
            else:
                lines.append(
                    DiffLine(
                        kind=DiffLineKind.CONTEXT,
                        content=raw[1:],
                        old_line=old_line,
                        new_line=new_line,
                    )
                )
                old_line += 1
                new_line += 1

        if header is not None:
            hunks.append(_build_hunk(header, lines))
        return tuple(hunks)


def _build_hunk(header: re.Match[str], lines: list[DiffLine]) -> DiffHunk:
    return DiffHunk(
        old_start=int(header.group(1)),
        old_count=int(header.group(2)) if header.group(2) is not None else 1,
        new_start=int(header.group(3)),
        new_count=int(header.group(4)) if header.group(4) is not None else 1,
        section_heading=header.group(5) or "",
        lines=tuple(lines),
    )
