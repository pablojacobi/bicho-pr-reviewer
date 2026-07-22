"""Async subprocess execution with a hard timeout and no shell."""

import asyncio
from collections.abc import Sequence
from pathlib import Path

from bicho.domain.ports.system import ProcessResult


class AsyncSubprocessRunner:
    """Runs commands via ``create_subprocess_exec`` (no shell) and kills them on timeout."""

    async def run(
        self, command: Sequence[str], *, timeout_seconds: float, cwd: Path | None = None
    ) -> ProcessResult:
        """Execute ``command``; on timeout, kill the process and report ``timed_out=True``."""
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout_seconds)
        except TimeoutError:
            process.kill()
            await process.wait()
            return ProcessResult(returncode=None, stdout=b"", stderr=b"", timed_out=True)
        return ProcessResult(
            returncode=process.returncode,
            stdout=stdout or b"",
            stderr=stderr or b"",
            timed_out=False,
        )
