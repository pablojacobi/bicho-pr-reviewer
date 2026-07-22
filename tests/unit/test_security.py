"""Tests for webhook HMAC signature verification."""

import hashlib
import hmac

from bicho.api.security import verify_signature

_SECRET = "s3cret"
_BODY = b'{"action":"opened"}'


def _signature(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_accepts_a_correct_signature() -> None:
    assert verify_signature(_SECRET, _BODY, _signature(_SECRET, _BODY)) is True


def test_rejects_a_missing_signature() -> None:
    assert verify_signature(_SECRET, _BODY, None) is False


def test_rejects_a_wrong_prefix() -> None:
    digest = hmac.new(_SECRET.encode(), _BODY, hashlib.sha256).hexdigest()
    assert verify_signature(_SECRET, _BODY, f"sha1={digest}") is False


def test_rejects_a_tampered_body() -> None:
    signature = _signature(_SECRET, _BODY)
    assert verify_signature(_SECRET, b'{"action":"closed"}', signature) is False
