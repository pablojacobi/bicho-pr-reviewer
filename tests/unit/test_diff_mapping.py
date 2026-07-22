"""Tests for mapping findings to commentable diff locations."""

from bicho.domain.models.diff import NormalizedDiff
from bicho.domain.models.finding import DiffSide
from bicho.domain.services.diff_mapping import can_anchor, commentable_lines


def test_commentable_lines_on_the_right_side(sample_diff: NormalizedDiff) -> None:
    assert commentable_lines(sample_diff.files[0], DiffSide.RIGHT) == {10, 11, 12}


def test_commentable_lines_on_the_left_side(sample_diff: NormalizedDiff) -> None:
    assert commentable_lines(sample_diff.files[0], DiffSide.LEFT) == {10, 11}


def test_can_anchor_true_for_lines_in_the_diff(sample_diff: NormalizedDiff) -> None:
    assert can_anchor(
        sample_diff, path="app/db.py", start_line=11, end_line=12, side=DiffSide.RIGHT
    )


def test_can_anchor_false_when_a_line_is_not_in_the_diff(sample_diff: NormalizedDiff) -> None:
    assert not can_anchor(
        sample_diff, path="app/db.py", start_line=99, end_line=99, side=DiffSide.RIGHT
    )


def test_can_anchor_false_when_file_is_not_in_the_diff(sample_diff: NormalizedDiff) -> None:
    assert not can_anchor(
        sample_diff, path="missing.py", start_line=10, end_line=10, side=DiffSide.RIGHT
    )
