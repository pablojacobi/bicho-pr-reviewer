"""Filesystem path safety and file classification.

Pure helpers used before materializing untrusted repository files into a sandboxed workspace: they
reject path traversal / absolute / Windows-style paths and classify files that should be skipped
(binary, generated, vendored, oversized). The only I/O is whatever the caller subsequently performs.
"""

from pathlib import Path, PurePosixPath

from bicho.domain.errors import UnsafePathError

#: Default maximum size (bytes) for a single file we are willing to scan.
MAX_FILE_BYTES = 1_000_000

_SKIP_MARKERS = (
    "node_modules/",
    "vendor/",
    "dist/",
    "build/",
    ".venv/",
    "site-packages/",
    "__pycache__/",
    ".min.",
    ".generated.",
    "_pb2.py",
)


def is_safe_relative_path(raw: str) -> bool:
    """Whether ``raw`` is a safe, repository-relative path (not empty/absolute/traversing)."""
    if not raw or "\x00" in raw or "\\" in raw or ":" in raw:
        return False
    pure = PurePosixPath(raw)
    if pure.is_absolute():
        return False
    return not any(part == ".." for part in pure.parts)


def resolve_within(base: Path, relative: str) -> Path:
    """Resolve ``relative`` under ``base``; raise ``UnsafePathError`` if it escapes ``base``."""
    if not is_safe_relative_path(relative):
        raise UnsafePathError(relative)
    base_resolved = base.resolve()
    resolved = (base / relative).resolve()
    if resolved != base_resolved and base_resolved not in resolved.parents:
        raise UnsafePathError(relative)
    return resolved


def is_probably_binary(data: bytes) -> bool:
    """Heuristic: treat content with a NUL byte in its first 8 KiB as binary."""
    return b"\x00" in data[:8192]


def is_generated_or_vendored(path: str) -> bool:
    """Whether ``path`` looks generated or vendored and should be skipped."""
    lowered = path.lower()
    return any(marker in lowered for marker in _SKIP_MARKERS)


def is_within_size(num_bytes: int, limit: int = MAX_FILE_BYTES) -> bool:
    """Whether ``num_bytes`` is within the allowed per-file size ``limit``."""
    return num_bytes <= limit
