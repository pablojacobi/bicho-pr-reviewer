"""Tests for GitHub App authentication (RESPX-mocked, no network)."""

from datetime import UTC, datetime, timedelta

import httpx
import jwt
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from bicho.infrastructure.github.auth import GitHubAppAuth

_INSTALLATION_ENDPOINT = "https://api.github.com/app/installations/42/access_tokens"


def _generate_private_key() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


_PRIVATE_KEY = _generate_private_key()


class _Clock:
    def __init__(self) -> None:
        self._now = datetime(2026, 7, 22, 12, 0, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)


def _token_response(token: str, clock: _Clock) -> httpx.Response:
    expires = clock.now() + timedelta(hours=1)
    return httpx.Response(201, json={"token": token, "expires_at": expires.isoformat()})


def _auth(http: httpx.AsyncClient, clock: _Clock) -> GitHubAppAuth:
    return GitHubAppAuth(app_id="123", private_key=_PRIVATE_KEY, clock=clock, http=http)


async def test_app_jwt_carries_the_issuer() -> None:
    async with httpx.AsyncClient() as http:
        token = _auth(http, _Clock()).app_jwt()

    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims["iss"] == "123"
    assert claims["exp"] > claims["iat"]


@respx.mock
async def test_installation_token_is_fetched_then_cached() -> None:
    clock = _Clock()
    route = respx.post(_INSTALLATION_ENDPOINT).mock(return_value=_token_response("tok-1", clock))
    async with httpx.AsyncClient() as http:
        auth = _auth(http, clock)
        first = await auth.installation_token(42)
        second = await auth.installation_token(42)

    assert (first, second) == ("tok-1", "tok-1")
    assert route.call_count == 1


@respx.mock
async def test_installation_token_refreshes_after_expiry() -> None:
    clock = _Clock()
    tokens = iter(["tok-1", "tok-2"])

    def _next(request: httpx.Request) -> httpx.Response:
        return _token_response(next(tokens), clock)

    route = respx.post(_INSTALLATION_ENDPOINT).mock(side_effect=_next)
    async with httpx.AsyncClient() as http:
        auth = _auth(http, clock)
        first = await auth.installation_token(42)
        clock.advance(3600)
        second = await auth.installation_token(42)

    assert (first, second) == ("tok-1", "tok-2")
    assert route.call_count == 2
