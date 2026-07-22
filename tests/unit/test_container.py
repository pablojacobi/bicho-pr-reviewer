"""Tests for the composition root (offline — objects are constructed, never called)."""

import httpx
from pydantic import SecretStr

from bicho.api.container import Container
from bicho.application.review_service import ReviewService
from bicho.config.settings import GitHubSettings, LLMSettings, Settings


def _settings() -> Settings:
    return Settings(
        github=GitHubSettings(app_id="1", private_key=SecretStr("key"), installation_id=7),
        llm=LLMSettings(api_key=SecretStr("test"), base_url="https://llm.test/v1"),
    )


async def test_container_builds_and_caches_the_review_service() -> None:
    async with httpx.AsyncClient() as http:
        container = Container(_settings(), http=http)
        first = container.review_service()
        second = container.review_service()

    assert isinstance(first, ReviewService)
    assert first is second
