"""Shared pytest fixtures and deterministic test hygiene."""

import os
from collections.abc import Callable, Iterator

import pytest
import structlog

from bicho.domain.models.diff import (
    DiffHunk,
    DiffLine,
    DiffLineKind,
    FileChangeKind,
    FileDiff,
    NormalizedDiff,
)
from bicho.domain.models.finding import Category, Confidence, Finding, Severity, SourceKind


@pytest.fixture(autouse=True)
def _clean_bicho_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove any ``BICHO_``-prefixed env vars so Settings load deterministically."""
    for key in list(os.environ):
        if key.startswith("BICHO_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def _reset_structlog() -> Iterator[None]:
    """Reset structlog global configuration after each test."""
    yield
    structlog.reset_defaults()


@pytest.fixture
def make_finding() -> Callable[..., Finding]:
    """Return a factory that builds a valid Finding, overriding any fields you pass."""

    def _make(**overrides: object) -> Finding:
        data: dict[str, object] = {
            "id": "f1",
            "fingerprint": "fp0000000000000a",
            "category": Category.SECURITY,
            "subcategory": "sql-injection",
            "severity": Severity.HIGH,
            "confidence": Confidence.MEDIUM,
            "title": "Title",
            "explanation": "Explanation.",
            "impact": "Impact.",
            "recommendation": "Recommendation.",
            "path": "app/db.py",
            "start_line": 10,
            "end_line": 12,
            "source_kind": SourceKind.LLM_ANALYZER,
            "source_name": "security",
            "head_sha": "sha",
            "language": "python",
        }
        data.update(overrides)
        return Finding.model_validate(data)

    return _make


@pytest.fixture
def sample_diff() -> NormalizedDiff:
    """A small diff for app/db.py: commentable RIGHT lines {10, 11, 12}, LEFT lines {10, 11}."""
    hunk = DiffHunk(
        old_start=10,
        old_count=2,
        new_start=10,
        new_count=3,
        lines=(
            DiffLine(kind=DiffLineKind.CONTEXT, content="ctx", old_line=10, new_line=10),
            DiffLine(kind=DiffLineKind.REMOVED, content="old", old_line=11),
            DiffLine(kind=DiffLineKind.ADDED, content="new_a", new_line=11),
            DiffLine(kind=DiffLineKind.ADDED, content="new_b", new_line=12),
        ),
    )
    return NormalizedDiff(
        files=(FileDiff(path="app/db.py", change_kind=FileChangeKind.MODIFIED, hunks=(hunk,)),)
    )
