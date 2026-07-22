"""Tests for the health, readiness, and version endpoints."""

import httpx
from pydantic import SecretStr

from bicho import __version__
from bicho.api.app import create_app
from bicho.config.settings import GitHubSettings, LLMSettings, ProviderSpec, Settings


def _client(app: httpx.ASGITransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=app, base_url="http://test")


async def test_healthz_returns_ok() -> None:
    async with _client(httpx.ASGITransport(app=create_app())) as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readyz_reports_not_ready_when_unconfigured() -> None:
    async with _client(httpx.ASGITransport(app=create_app())) as client:
        response = await client.get("/readyz")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["problems"]


async def test_readyz_reports_ready_when_configured() -> None:
    settings = Settings(
        github=GitHubSettings(app_id="1", private_key=SecretStr("key"), installation_id=7),
        llm=LLMSettings(
            providers={
                "minimax": ProviderSpec(api_key=SecretStr("k"), base_url="https://x/v1", model="m")
            }
        ),
    )
    async with _client(httpx.ASGITransport(app=create_app(settings))) as client:
        response = await client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


async def test_version_reports_the_versions() -> None:
    async with _client(httpx.ASGITransport(app=create_app())) as client:
        response = await client.get("/version")

    assert response.status_code == 200
    assert response.json()["version"] == __version__
