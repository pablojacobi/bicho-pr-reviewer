"""Centralized application configuration.

All environment access lives here (and only here): the rest of the codebase depends on a typed,
validated ``Settings`` object rather than reading environment variables directly. Values are read
from the environment with the ``BICHO_`` prefix; nested sections (added as features land) use the
``__`` delimiter, e.g. ``BICHO_GITHUB__APP_ID``.
"""

import logging

from pydantic import BaseModel, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from bicho.config.environment import Environment


class GitHubSettings(BaseModel):
    """GitHub App credentials and API base (env: ``BICHO_GITHUB__*``)."""

    app_id: str = ""
    private_key: SecretStr = SecretStr("")
    installation_id: int = 0
    api_base: str = "https://api.github.com"
    webhook_secret: SecretStr = SecretStr("")

    @field_validator("private_key", mode="before")
    @classmethod
    def _restore_pem_newlines(cls, value: object) -> object:
        r"""Turn literal ``\n`` in an env-provided single-line PEM back into real newlines."""
        if isinstance(value, str):
            return value.replace("\\n", "\n")
        return value


class LLMSettings(BaseModel):
    """Model endpoint configuration (env: ``BICHO_LLM__*``).

    Defaults target MiniMax's OpenAI-compatible endpoint; the model id and base URL are plain
    configuration so nothing MiniMax-specific is hard-coded.
    """

    api_key: SecretStr = SecretStr("")
    base_url: str = "https://api.minimax.io/v1"
    model: str = "MiniMax-M3"
    timeout_seconds: float = 60.0


class ScannerSettings(BaseModel):
    """Deterministic-scanner configuration (env: ``BICHO_SCANNER__*``).

    Semgrep is optional so the app runs where the binary is absent (it degrades to LLM analyzers).
    """

    semgrep_enabled: bool = True
    semgrep_config: str = "resources/semgrep"
    semgrep_timeout_seconds: float = 60.0
    # pip-audit queries a vulnerability database over the network; disable it when offline.
    pip_audit_enabled: bool = True
    pip_audit_timeout_seconds: float = 60.0


class Settings(BaseSettings):
    """Typed, validated application settings."""

    model_config = SettingsConfigDict(
        env_prefix="BICHO_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    environment: Environment = Environment.LOCAL
    log_level: str = "INFO"
    # None => derive from the environment (JSON logs in production, human-readable elsewhere).
    json_logs: bool | None = None

    github: GitHubSettings = GitHubSettings()
    llm: LLMSettings = LLMSettings()
    scanner: ScannerSettings = ScannerSettings()

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in logging.getLevelNamesMapping():
            raise ValueError(f"invalid log level: {value!r}")
        return normalized

    @property
    def render_json_logs(self) -> bool:
        """Whether logs render as JSON (production default, overridable)."""
        if self.json_logs is None:
            return self.environment.is_production
        return self.json_logs
