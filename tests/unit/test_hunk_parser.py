"""Tests for the unified-diff hunk parser."""

from bicho.domain.models.diff import DiffLineKind
from bicho.domain.ports.diff_parser import DiffParserPort
from bicho.infrastructure.diff.hunk_parser import DiffParser


def test_parses_context_added_and_removed_with_line_numbers() -> None:
    patch = (
        "@@ -10,3 +10,4 @@ def handler():\n"
        " context_before\n"
        "-old_line\n"
        "+new_line_a\n"
        "+new_line_b\n"
        " context_after\n"
    )

    hunks = DiffParser().parse_hunks(patch)

    assert len(hunks) == 1
    hunk = hunks[0]
    assert (hunk.old_start, hunk.old_count, hunk.new_start, hunk.new_count) == (10, 3, 10, 4)
    assert hunk.section_heading == "def handler():"

    before, removed, added_a, added_b, after = hunk.lines
    assert (before.kind, before.old_line, before.new_line) == (DiffLineKind.CONTEXT, 10, 10)
    assert (removed.kind, removed.old_line, removed.new_line) == (DiffLineKind.REMOVED, 11, None)
    assert (added_a.kind, added_a.old_line, added_a.new_line) == (DiffLineKind.ADDED, None, 11)
    assert (added_b.kind, added_b.new_line) == (DiffLineKind.ADDED, 12)
    assert (after.kind, after.old_line, after.new_line) == (DiffLineKind.CONTEXT, 12, 13)
    assert added_a.content == "new_line_a"


def test_hunk_header_without_counts_defaults_to_one() -> None:
    hunks = DiffParser().parse_hunks("@@ -5 +7 @@\n-a\n+b\n")

    hunk = hunks[0]
    assert (hunk.old_start, hunk.old_count, hunk.new_start, hunk.new_count) == (5, 1, 7, 1)
    assert hunk.section_heading == ""


def test_no_newline_marker_is_ignored() -> None:
    patch = "@@ -1,2 +1,2 @@\n a\n-b\n+c\n\\ No newline at end of file\n"

    hunk = DiffParser().parse_hunks(patch)[0]

    assert [line.kind for line in hunk.lines] == [
        DiffLineKind.CONTEXT,
        DiffLineKind.REMOVED,
        DiffLineKind.ADDED,
    ]


def test_multiple_hunks_are_parsed_separately() -> None:
    patch = "@@ -1,1 +1,1 @@\n-a\n+b\n@@ -10,1 +10,1 @@\n-c\n+d\n"

    hunks = DiffParser().parse_hunks(patch)

    assert len(hunks) == 2
    assert hunks[0].old_start == 1
    assert hunks[1].old_start == 10


def test_preamble_before_first_hunk_is_ignored() -> None:
    hunks = DiffParser().parse_hunks("garbage before the hunk\n@@ -1 +1 @@\n-a\n+b\n")

    assert len(hunks) == 1


def test_empty_patch_yields_no_hunks() -> None:
    assert DiffParser().parse_hunks("") == ()


def test_diff_parser_satisfies_the_port() -> None:
    parser: DiffParserPort = DiffParser()

    assert parser.parse_hunks("@@ -1 +1 @@\n-a\n+b\n")[0].new_start == 1
