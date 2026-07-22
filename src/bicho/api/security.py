"""Webhook signature verification.

GitHub signs each webhook with HMAC-SHA256 over the raw body, sent as ``X-Hub-Signature-256:
sha256=<hex>``. Verification uses the *raw* bytes (never the re-serialized JSON) and a constant-time
compare, so a wrong or missing signature is rejected before the body is parsed.
"""

import hashlib
import hmac

_PREFIX = "sha256="


def verify_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
    """Return whether ``signature_header`` is a valid HMAC-SHA256 of ``body`` under ``secret``."""
    if not signature_header or not signature_header.startswith(_PREFIX):
        return False
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"{_PREFIX}{digest}", signature_header)
