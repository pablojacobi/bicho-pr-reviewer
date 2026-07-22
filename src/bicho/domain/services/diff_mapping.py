"""Mapping findings to commentable diff locations.

GitHub only accepts an inline comment on a line that is part of the diff: on the RIGHT side an added
or context line (it has a new-file number); on the LEFT side a removed or context line (old-file
number). These helpers answer "can this ``(path, line-range, side)`` be anchored?".
"""

from bicho.domain.models.diff import FileDiff, NormalizedDiff
from bicho.domain.models.finding import DiffSide


def commentable_lines(file_diff: FileDiff, side: DiffSide) -> set[int]:
    """The set of file line numbers that can be commented on for the given ``side``."""
    lines: set[int] = set()
    for hunk in file_diff.hunks:
        for line in hunk.lines:
            number = line.new_line if side is DiffSide.RIGHT else line.old_line
            if number is not None:
                lines.add(number)
    return lines


def can_anchor(
    diff: NormalizedDiff, *, path: str, start_line: int, end_line: int, side: DiffSide
) -> bool:
    """Whether an inline comment can be anchored to ``[start_line, end_line]`` on ``side``."""
    file_diff = diff.file(path)
    if file_diff is None:
        return False
    lines = commentable_lines(file_diff, side)
    return start_line in lines and end_line in lines
