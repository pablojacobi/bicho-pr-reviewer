"""Tests for configuration readiness checks."""

from pydantic import SecretStr

from bicho.config.readiness import missing_requirements
from bicho.config.settings import GitHubSettings, LLMSettings, ProviderSpec, Settings


def _ready_settings() -> Settings:
    return Settings(
        github=GitHubSettings(app_id="1", private_key=SecretStr("key"), installation_id=7),
        llm=LLMSettings(
            providers={
                "minimax": ProviderSpec(api_key=SecretStr("k"), base_url="https://x/v1", model="m")
            }
        ),
    )


def test_complete_configuration_has_no_problems() -> None:
    assert missing_requirements(_ready_settings()) == []


def test_empty_configuration_reports_every_missing_requirement() -> None:
    problems = missing_requirements(Settings())

    assert len(problems) == 4
    assert any("app_id" in problem for problem in problems)
    assert any("private_key" in problem for problem in problems)
    assert any("installation_id" in problem for problem in problems)
    assert any("llm" in problem for problem in problems)


def test_incomplete_active_provider_is_reported() -> None:
    settings = Settings(
        github=GitHubSettings(app_id="1", private_key=SecretStr("key"), installation_id=7),
        llm=LLMSettings(providers={"minimax": ProviderSpec(api_key=SecretStr("k"))}),
    )

    problems = missing_requirements(settings)

    assert any("missing api_key/base_url/model" in problem for problem in problems)
