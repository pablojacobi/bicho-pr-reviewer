"""Stable finding fingerprints.

A fingerprint identifies the *same issue* across re-runs and small line drift, so a finding survives
unrelated edits elsewhere in the file. It deliberately excludes line numbers and severity (both
volatile) and anchors to the code's shape via a whitespace-normalized hash of the offending snippet.
"""

import hashlib
import re

_WHITESPACE = re.compile(r"\s+")
_UNIT_SEPARATOR = "\x1f"


def _normalize_snippet(snippet: str) -> str:
    return _WHITESPACE.sub(" ", snippet).strip()


def _normalize_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def compute_fingerprint(
    *,
    path: str,
    category: str,
    subcategory: str,
    rule_key: str,
    enclosing_symbol: str | None,
    snippet: str,
) -> str:
    """Compute a stable 16-hex-character fingerprint for a finding's identity."""
    snippet_digest = hashlib.sha256(_normalize_snippet(snippet).encode("utf-8")).hexdigest()
    components = [
        _normalize_path(path),
        category,
        subcategory,
        rule_key,
        enclosing_symbol or "",
        snippet_digest,
    ]
    joined = _UNIT_SEPARATOR.join(components)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]
