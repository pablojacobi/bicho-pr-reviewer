"""A deterministic ``SubprocessRunner`` fake for tests and offline runs.

Returns a pre-scripted ``ProcessResult`` and records the commands it was asked to run, so scanner
logic can be exercised without invoking a real binary.
"""

from collections.abc import Sequence
from pathlib import Path

from bicho.domain.ports.system import ProcessResult


class FakeSubprocessRunner:
    """Returns a fixed ``ProcessResult`` and records every command."""

    def __init__(self, result: ProcessResult) -> None:
        self._result = result
        self.commands: list[Sequence[str]] = []

    async def run(
        self, command: Sequence[str], *, timeout_seconds: float, cwd: Path | None = None
    ) -> ProcessResult:
        self.commands.append(command)
        return self._result
