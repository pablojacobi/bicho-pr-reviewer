"""Property-based tests for the hunk parser: line numbers stay consistent for any op sequence."""

from hypothesis import given
from hypothesis import strategies as st

from bicho.domain.models.diff import DiffLineKind
from bicho.infrastructure.diff.hunk_parser import DiffParser

_OPS = st.lists(st.sampled_from(["ctx", "add", "del"]), min_size=1, max_size=25)


@given(ops=_OPS, old_start=st.integers(min_value=1, max_value=500), new_start=st.integers(1, 500))
def test_parsed_line_numbers_track_the_op_sequence(
    ops: list[str], old_start: int, new_start: int
) -> None:
    prefix = {"ctx": " ctx", "add": "+add", "del": "-del"}
    old_count = sum(op != "add" for op in ops)
    new_count = sum(op != "del" for op in ops)
    patch = (
        f"@@ -{old_start},{old_count} +{new_start},{new_count} @@\n"
        + "\n".join(prefix[op] for op in ops)
        + "\n"
    )

    hunks = DiffParser().parse_hunks(patch)

    assert len(hunks) == 1
    hunk = hunks[0]
    assert (hunk.old_start, hunk.new_start) == (old_start, new_start)
    assert len(hunk.lines) == len(ops)

    expected_old = old_start
    expected_new = new_start
    for line, op in zip(hunk.lines, ops, strict=True):
        if op == "ctx":
            assert line.kind is DiffLineKind.CONTEXT
            assert line.old_line == expected_old
            assert line.new_line == expected_new
            expected_old += 1
            expected_new += 1
        elif op == "add":
            assert line.kind is DiffLineKind.ADDED
            assert line.old_line is None
            assert line.new_line == expected_new
            expected_new += 1
        else:
            assert line.kind is DiffLineKind.REMOVED
            assert line.new_line is None
            assert line.old_line == expected_old
            expected_old += 1
