"""Shared pytest fixtures and deterministic test hygiene."""

import os
from collections.abc import Iterator

import pytest
import structlog


@pytest.fixture(autouse=True)
def _clean_bicho_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove any ``BICHO_``-prefixed env vars so Settings load deterministically."""
    for key in list(os.environ):
        if key.startswith("BICHO_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def _reset_structlog() -> Iterator[None]:
    """Reset structlog global configuration after each test."""
    yield
    structlog.reset_defaults()
