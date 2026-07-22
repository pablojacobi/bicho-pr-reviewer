"""Tests for application settings loading and validation."""

import pytest
from pydantic import SecretStr, ValidationError

from bicho.config.environment import Environment
from bicho.config.settings import GitHubSettings, LLMSettings, Settings


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


def test_github_private_key_restores_escaped_newlines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BICHO_GITHUB__PRIVATE_KEY", "-----BEGIN-----\\nBODY\\n-----END-----")

    settings = Settings()

    assert settings.github.private_key.get_secret_value() == "-----BEGIN-----\nBODY\n-----END-----"


def test_github_private_key_keeps_real_newlines_unchanged() -> None:
    github = GitHubSettings(private_key=SecretStr("line1\nline2"))

    assert github.private_key.get_secret_value() == "line1\nline2"


def test_multiple_llm_providers_load_from_env_and_active_selects_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BICHO_LLM__ACTIVE", "gemini")
    monkeypatch.setenv("BICHO_LLM__PROVIDERS__MINIMAX__API_KEY", "mk")
    monkeypatch.setenv("BICHO_LLM__PROVIDERS__MINIMAX__BASE_URL", "https://api.minimax.io/v1")
    monkeypatch.setenv("BICHO_LLM__PROVIDERS__MINIMAX__MODEL", "minimax-m3")
    monkeypatch.setenv("BICHO_LLM__PROVIDERS__GEMINI__API_KEY", "gk")
    monkeypatch.setenv("BICHO_LLM__PROVIDERS__GEMINI__BASE_URL", "https://gemini/openai")
    monkeypatch.setenv("BICHO_LLM__PROVIDERS__GEMINI__MODEL", "gemini-2.0-flash")

    llm = Settings().llm

    assert set(llm.providers) == {"minimax", "gemini"}
    active = llm.active_provider()
    assert active.model == "gemini-2.0-flash"
    assert active.api_key.get_secret_value() == "gk"


def test_active_provider_is_empty_when_unconfigured() -> None:
    assert LLMSettings(active="minimax", providers={}).active_provider().model == ""
