"""A Python language adapter (the first concrete language target).

Its value over the generic fallback is ``ast``-based enclosing-symbol resolution: a finding's
fingerprint anchors to the function/class that contains it, so the finding survives unrelated line
drift elsewhere in the file. It also scopes analysis to Python source and dependency manifests.
"""

import ast
from collections.abc import Sequence

from bicho.domain.models.pull_request import ChangedFile
from bicho.infrastructure.fs.pathsafe import is_generated_or_vendored, is_safe_relative_path

_ANALYZERS = (
    "correctness",
    "security",
    "performance",
    "maintainability",
    "tests",
    "contracts",
    "semgrep",
    "pip-audit",
)
_MANIFESTS = frozenset({"pyproject.toml", "setup.py", "setup.cfg"})
_SYMBOL_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _is_python_relevant(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    if path.endswith(".py") or name in _MANIFESTS:
        return True
    return name.startswith("requirements") and name.endswith(".txt")


class PythonAdapter:
    """Language adapter for Python repositories."""

    language = "python"

    def score(self, files: Sequence[ChangedFile]) -> float:
        return 0.9 if any(file.filename.endswith(".py") for file in files) else 0.0

    def in_scope(self, file: ChangedFile) -> bool:
        if file.patch is None or not is_safe_relative_path(file.filename):
            return False
        if is_generated_or_vendored(file.filename):
            return False
        return _is_python_relevant(file.filename)

    def default_analyzers(self) -> tuple[str, ...]:
        return _ANALYZERS

    def enclosing_symbol(self, path: str, content: str, line: int) -> str | None:
        """Return the name of the innermost def/class containing ``line`` (or ``None``)."""
        if not path.endswith(".py"):
            return None
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return None
        # ast.walk is breadth-first, so an outer def/class is always visited before an inner one;
        # the last node that still contains the line is therefore the innermost.
        symbol: str | None = None
        for node in ast.walk(tree):
            if not isinstance(node, _SYMBOL_NODES):
                continue
            end = node.end_lineno or node.lineno
            if node.lineno <= line <= end:
                symbol = node.name
        return symbol
