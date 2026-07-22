"""Composition root: assembles the review pipeline from settings and shared clients.

This is the single place where concrete infrastructure (GitHub client, model provider, diff parser,
adapters, analyzers) is wired together into a :class:`ReviewService`. Everything upstream depends on
ports, so this module is the only one that knows every concrete type. The shared ``httpx`` client is
owned by the app lifespan and injected here, so nothing constructs its own transport.
"""

from collections.abc import Mapping

import httpx

from bicho.application.analyzers.base import Analyzer
from bicho.application.analyzers.registry import build_analyzers
from bicho.application.graph.builder import build_graph
from bicho.application.review_service import ReviewService
from bicho.config.settings import Settings
from bicho.domain.ports.model_provider import ModelProvider
from bicho.domain.ports.system import Clock, IdGenerator, SubprocessRunner, TempWorkspace
from bicho.infrastructure.clock import SystemClock
from bicho.infrastructure.diff.hunk_parser import DiffParser
from bicho.infrastructure.fs.workspace import TempWorkspaceFactory
from bicho.infrastructure.github.auth import GitHubAppAuth
from bicho.infrastructure.github.client import GitHubClient
from bicho.infrastructure.ids import UuidGenerator
from bicho.infrastructure.language.generic import GenericAdapter
from bicho.infrastructure.language.python_adapter import PythonAdapter
from bicho.infrastructure.language.registry import AdapterRegistry
from bicho.infrastructure.model.registry import ModelSpec, build_model_provider
from bicho.infrastructure.process.subprocess_runner import AsyncSubprocessRunner
from bicho.infrastructure.scanners.pip_audit_runner import build_dependency_audit_scanner
from bicho.infrastructure.scanners.semgrep_runner import build_semgrep_scanner


class Container:
    """Builds a ``ReviewService`` from settings, caching the assembled service."""

    def __init__(
        self,
        settings: Settings,
        *,
        http: httpx.AsyncClient,
        clock: Clock | None = None,
        ids: IdGenerator | None = None,
        subprocess_runner: SubprocessRunner | None = None,
        workspace: TempWorkspace | None = None,
    ) -> None:
        self._settings = settings
        self._http = http
        self._clock: Clock = clock or SystemClock()
        self._ids: IdGenerator = ids or UuidGenerator()
        self._runner: SubprocessRunner = subprocess_runner or AsyncSubprocessRunner()
        self._workspace: TempWorkspace = workspace or TempWorkspaceFactory()
        self._services: dict[int, ReviewService] = {}

    def review_service(self, installation_id: int | None = None) -> ReviewService:
        """Return the review service for an installation (the settings default if unspecified).

        A webhook carries its own installation id; the manual endpoint falls back to the configured
        default. Services are cached per installation so tokens are minted per installation.
        """
        resolved = (
            installation_id
            if installation_id is not None
            else self._settings.github.installation_id
        )
        if resolved not in self._services:
            self._services[resolved] = self._build_service(resolved)
        return self._services[resolved]

    def _build_service(self, installation_id: int) -> ReviewService:
        model = self._model_provider()
        analyzers = self._analyzers(model)
        return ReviewService(
            graph=build_graph(list(analyzers)),
            github=self._github(installation_id),
            diff_parser=DiffParser(),
            adapters=AdapterRegistry([PythonAdapter()], fallback=GenericAdapter()),
            analyzers=analyzers,
            ids=self._ids,
            timeout_seconds=self._settings.review_timeout_seconds,
        )

    def _github(self, installation_id: int) -> GitHubClient:
        github = self._settings.github
        auth = GitHubAppAuth(
            app_id=github.app_id,
            private_key=github.private_key.get_secret_value(),
            clock=self._clock,
            http=self._http,
            api_base=github.api_base,
        )
        return GitHubClient(
            auth=auth,
            installation_id=installation_id,
            http=self._http,
            api_base=github.api_base,
        )

    def _model_provider(self) -> ModelProvider:
        provider = self._settings.llm.active_provider()
        return build_model_provider(
            ModelSpec(
                model=provider.model,
                api_key=provider.api_key.get_secret_value(),
                base_url=provider.base_url,
                timeout_seconds=provider.timeout_seconds,
                max_attempts=provider.max_attempts,
                retry_delay_seconds=provider.retry_delay_seconds,
                max_concurrency=provider.max_concurrency,
            )
        )

    def _analyzers(self, model: ModelProvider) -> Mapping[str, Analyzer]:
        analyzers: dict[str, Analyzer] = dict(build_analyzers(model=model, ids=self._ids))
        scanner = self._settings.scanner
        if scanner.semgrep_enabled:
            analyzers["semgrep"] = build_semgrep_scanner(
                runner=self._runner,
                workspace=self._workspace,
                ids=self._ids,
                config=scanner.semgrep_config,
                timeout_seconds=scanner.semgrep_timeout_seconds,
            )
        if scanner.pip_audit_enabled:
            analyzers["pip-audit"] = build_dependency_audit_scanner(
                runner=self._runner,
                workspace=self._workspace,
                ids=self._ids,
                timeout_seconds=scanner.pip_audit_timeout_seconds,
            )
        return analyzers
