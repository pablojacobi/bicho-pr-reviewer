"""Temporary workspace with guaranteed cleanup."""

import shutil
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path


class TempWorkspaceFactory:
    """Creates isolated temporary directories and always removes them afterwards."""

    def __init__(self, *, prefix: str = "bicho-", root: Path | None = None) -> None:
        self._prefix = prefix
        self._root = root

    @contextmanager
    def create(self) -> Generator[Path]:
        """Yield a fresh temporary directory, removing it and its contents on exit."""
        path = Path(tempfile.mkdtemp(prefix=self._prefix, dir=self._root))
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)
