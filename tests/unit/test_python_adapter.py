"""Tests for the Python language adapter."""

from bicho.domain.models.pull_request import ChangedFile
from bicho.infrastructure.language.python_adapter import PythonAdapter

_SOURCE = """\
import os


class Orders:
    def total(self, items):
        subtotal = sum(items)
        return subtotal


def average(values):
    return sum(values) / len(values)
"""


def _changed(filename: str, *, patch: str | None = "@@") -> ChangedFile:
    return ChangedFile(filename=filename, status="modified", patch=patch)


def test_scores_high_when_python_files_are_present() -> None:
    adapter = PythonAdapter()

    assert adapter.score([_changed("app/main.py")]) == 0.9
    assert adapter.score([_changed("README.md")]) == 0.0


def test_in_scope_covers_python_and_manifests_only() -> None:
    adapter = PythonAdapter()

    assert adapter.in_scope(_changed("app/main.py")) is True
    assert adapter.in_scope(_changed("requirements-dev.txt")) is True
    assert adapter.in_scope(_changed("pyproject.toml")) is True
    assert adapter.in_scope(_changed("README.md")) is False
    assert adapter.in_scope(_changed("app/main.py", patch=None)) is False
    assert adapter.in_scope(_changed("../evil.py")) is False
    assert adapter.in_scope(_changed("build/generated.py")) is False


def test_default_analyzers_include_scanners() -> None:
    analyzers = PythonAdapter().default_analyzers()

    assert "semgrep" in analyzers
    assert "pip-audit" in analyzers
    assert "correctness" in analyzers


def test_enclosing_symbol_resolves_innermost_def() -> None:
    adapter = PythonAdapter()

    # line 6 is inside Orders.total (nested in the class) — the innermost wins.
    assert adapter.enclosing_symbol("app/orders.py", _SOURCE, 6) == "total"
    # line 11 is inside the module-level average function.
    assert adapter.enclosing_symbol("app/orders.py", _SOURCE, 11) == "average"
    # line 2 (a blank line at module scope) is inside no def/class.
    assert adapter.enclosing_symbol("app/orders.py", _SOURCE, 2) is None


def test_enclosing_symbol_returns_none_for_non_python_or_unparseable() -> None:
    adapter = PythonAdapter()

    assert adapter.enclosing_symbol("notes.md", "def f(): pass", 1) is None
    assert adapter.enclosing_symbol("broken.py", "def f(:\n    pass", 1) is None
