"""Tests for structured logging configuration."""

import structlog

from bicho.config.environment import Environment
from bicho.config.logging import configure_logging, scrub_sensitive
from bicho.config.settings import Settings


def test_scrub_sensitive_redacts_known_keys_only() -> None:
    event = {"Authorization": "Bearer x", "message": "hello", "api_key": "k"}

    result = scrub_sensitive(None, "info", event)  # type: ignore[arg-type]

    assert result["Authorization"] == "***redacted***"
    assert result["api_key"] == "***redacted***"
    assert result["message"] == "hello"


def test_configure_logging_uses_json_renderer_in_production() -> None:
    configure_logging(Settings(environment=Environment.PRODUCTION))

    processors = structlog.get_config()["processors"]

    assert isinstance(processors[-1], structlog.processors.JSONRenderer)


def test_configure_logging_uses_console_renderer_otherwise() -> None:
    configure_logging(Settings(environment=Environment.LOCAL))

    processors = structlog.get_config()["processors"]

    assert isinstance(processors[-1], structlog.dev.ConsoleRenderer)
