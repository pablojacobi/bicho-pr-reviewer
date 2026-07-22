"""Property-based tests for path safety: no safe input escapes, no traversal input is accepted."""

import string
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from bicho.domain.errors import UnsafePathError
from bicho.infrastructure.fs import pathsafe

# A base directory used purely for path arithmetic; it need not exist on disk.
_BASE = Path("/srv/bicho/base")

# Individually safe path segments: no separators, NUL, colon, backslash; never "." or "..".
_SAFE_ALPHABET = string.ascii_letters + string.digits + "-_.~"
_safe_segment = st.text(alphabet=_SAFE_ALPHABET, min_size=1, max_size=12).filter(
    lambda s: s not in {".", ".."}
)


@given(st.lists(_safe_segment, min_size=1, max_size=6))
def test_safe_paths_always_resolve_within_base(parts: list[str]) -> None:
    relative = "/".join(parts)
    assert pathsafe.is_safe_relative_path(relative) is True

    resolved = pathsafe.resolve_within(_BASE, relative)

    base_resolved = _BASE.resolve()
    assert resolved == base_resolved or base_resolved in resolved.parents


@given(st.lists(_safe_segment, min_size=0, max_size=3))
def test_paths_with_parent_traversal_are_always_rejected(parts: list[str]) -> None:
    relative = "/".join([*parts, "..", *parts]) if parts else ".."

    assert pathsafe.is_safe_relative_path(relative) is False
    try:
        pathsafe.resolve_within(_BASE, relative)
    except UnsafePathError:
        return
    raise AssertionError("expected UnsafePathError for a traversal path")
