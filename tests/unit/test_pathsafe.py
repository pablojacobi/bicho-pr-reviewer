"""Tests for filesystem path safety and file classification."""

from pathlib import Path

import pytest

from bicho.domain.errors import UnsafePathError
from bicho.infrastructure.fs import pathsafe


def test_is_safe_relative_path_accepts_a_normal_path() -> None:
    assert pathsafe.is_safe_relative_path("src/app.py") is True


@pytest.mark.parametrize("bad", ["", "\x00x", "/etc/passwd", "a/../b", "a\\b", "C:/x"])
def test_is_safe_relative_path_rejects_unsafe_inputs(bad: str) -> None:
    assert pathsafe.is_safe_relative_path(bad) is False


def test_resolve_within_returns_path_under_base(tmp_path: Path) -> None:
    resolved = pathsafe.resolve_within(tmp_path, "sub/dir/file.py")

    assert resolved == (tmp_path / "sub" / "dir" / "file.py").resolve()


def test_resolve_within_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(UnsafePathError):
        pathsafe.resolve_within(tmp_path, "../escape.py")


def test_resolve_within_rejects_symlink_escape(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (base / "link").symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafePathError):
        pathsafe.resolve_within(base, "link/evil.py")


def test_is_probably_binary_detects_nul_bytes() -> None:
    assert pathsafe.is_probably_binary(b"plain text") is False
    assert pathsafe.is_probably_binary(b"has\x00nul") is True


def test_is_generated_or_vendored() -> None:
    assert pathsafe.is_generated_or_vendored("app/node_modules/x.js") is True
    assert pathsafe.is_generated_or_vendored("src/app.py") is False


def test_is_within_size() -> None:
    assert pathsafe.is_within_size(10) is True
    assert pathsafe.is_within_size(pathsafe.MAX_FILE_BYTES + 1) is False
