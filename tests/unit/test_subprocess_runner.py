"""Tests for the async subprocess runner (uses the venv Python as a deterministic child)."""

import sys

from bicho.domain.ports.system import ProcessResult, SubprocessRunner
from bicho.infrastructure.process.subprocess_runner import AsyncSubprocessRunner


async def test_run_captures_stdout_and_zero_returncode() -> None:
    runner: SubprocessRunner = AsyncSubprocessRunner()

    result = await runner.run([sys.executable, "-c", "print('hello')"], timeout_seconds=10)

    assert isinstance(result, ProcessResult)
    assert result.timed_out is False
    assert result.returncode == 0
    assert b"hello" in result.stdout


async def test_run_reports_nonzero_returncode() -> None:
    runner = AsyncSubprocessRunner()

    result = await runner.run([sys.executable, "-c", "import sys; sys.exit(3)"], timeout_seconds=10)

    assert result.timed_out is False
    assert result.returncode == 3


async def test_run_times_out_and_kills_the_process() -> None:
    runner = AsyncSubprocessRunner()

    result = await runner.run(
        [sys.executable, "-c", "import time; time.sleep(30)"], timeout_seconds=0.2
    )

    assert result.timed_out is True
    assert result.returncode is None
    assert result.stdout == b""
