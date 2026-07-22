"""Tests for the normalized diff models."""

from bicho.domain.models.diff import FileChangeKind, FileDiff, NormalizedDiff


def test_normalized_diff_file_lookup_finds_the_file() -> None:
    target = FileDiff(path="app/x.py", change_kind=FileChangeKind.MODIFIED)
    diff = NormalizedDiff(
        files=(target, FileDiff(path="other.py", change_kind=FileChangeKind.ADDED))
    )

    assert diff.file("app/x.py") == target


def test_normalized_diff_file_lookup_returns_none_when_missing() -> None:
    diff = NormalizedDiff(files=(FileDiff(path="a.py", change_kind=FileChangeKind.ADDED),))

    assert diff.file("missing.py") is None


def test_file_diff_defaults() -> None:
    file_diff = FileDiff(path="a.py", change_kind=FileChangeKind.ADDED)

    assert file_diff.previous_path is None
    assert file_diff.is_binary is False
    assert file_diff.hunks == ()
