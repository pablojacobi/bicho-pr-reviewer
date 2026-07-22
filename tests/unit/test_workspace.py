"""Tests for the temporary workspace factory."""

from pathlib import Path

import pytest

from bicho.domain.ports.system import TempWorkspace
from bicho.infrastructure.fs.workspace import TempWorkspaceFactory


def test_workspace_is_created_then_removed(tmp_path: Path) -> None:
    factory: TempWorkspace = TempWorkspaceFactory(root=tmp_path)

    created: Path | None = None
    with factory.create() as workspace:
        created = workspace
        assert workspace.exists()
        (workspace / "file.txt").write_text("content")

    assert created is not None
    assert not created.exists()


def test_workspace_is_removed_even_on_exception(tmp_path: Path) -> None:
    factory = TempWorkspaceFactory(root=tmp_path)

    created: Path | None = None
    with pytest.raises(RuntimeError):  # noqa: SIM117 — nested `with` clarifies which block raises
        with factory.create() as workspace:
            created = workspace
            raise RuntimeError("boom")

    assert created is not None
    assert not created.exists()
