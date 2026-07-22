"""Ports for system-level side effects.

These Protocols are the seams that keep the wall clock, randomness, subprocesses, and the filesystem
out of the domain and application layers, so behaviour is deterministic and fully fakeable.
"""

from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProcessResult:
    """Outcome of a subprocess execution."""

    returncode: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool


class Clock(Protocol):
    """Provides the current time (always timezone-aware, UTC)."""

    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    """Generates unique identifiers."""

    def new_id(self) -> str: ...


class SubprocessRunner(Protocol):
    """Runs an external command without a shell, bounded by a hard timeout."""

    async def run(
        self, command: Sequence[str], *, timeout_seconds: float, cwd: Path | None = None
    ) -> ProcessResult: ...


class TempWorkspace(Protocol):
    """Creates isolated temporary directories with guaranteed cleanup."""

    def create(self) -> AbstractContextManager[Path]: ...
