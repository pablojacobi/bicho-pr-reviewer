"""Tests for application settings loading and validation."""

import pytest
from pydantic import ValidationError

from bicho.config.environment import Environment
from bicho.config.settings import Settings


def test_defaults_are_local_and_non_json() -> None:
    settings = Settings()

    assert settings.environment is Environment.LOCAL
    assert settings.log_level == "INFO"
    assert settings.json_logs is None
    assert settings.render_json_logs is False


def test_environment_is_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BICHO_ENVIRONMENT", "production")

    settings = Settings()

    assert settings.environment is Environment.PRODUCTION
    assert settings.render_json_logs is True


def test_log_level_is_normalized_to_upper() -> None:
    assert Settings(log_level="debug").log_level == "DEBUG"


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(log_level="not-a-level")


def test_explicit_json_logs_override_the_environment_default() -> None:
    assert Settings(json_logs=True).render_json_logs is True
    assert Settings(environment=Environment.PRODUCTION, json_logs=False).render_json_logs is False
