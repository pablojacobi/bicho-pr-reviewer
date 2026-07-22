"""Composition root: assembles the review pipeline from settings and shared clients.

This is the single place where concrete infrastructure (GitHub client, model provider, diff parser,
adapters, analyzers) is wired together into a :class:`ReviewService`. Everything upstream depends on
ports, so this module is the only one that knows every concrete type. The shared ``httpx`` client is
owned by the app lifespan and injected here, so nothing constructs its own transport.
"""

from collections.abc import Mapping

import httpx

from bicho.application.analyzers.base import Analyzer
from bicho.application.analyzers.correctness import build_correctness_analyzer
from bicho.application.graph.builder import build_graph
from bicho.application.review_service import ReviewService
from bicho.config.settings import Settings
from bicho.domain.ports.model_provider import ModelProvider
from bicho.domain.ports.system import Clock, IdGenerator
from bicho.infrastructure.clock import SystemClock
from bicho.infrastructure.diff.hunk_parser import DiffParser
from bicho.infrastructure.github.auth import GitHubAppAuth
from bicho.infrastructure.github.client import GitHubClient
from bicho.infrastructure.ids import UuidGenerator
from bicho.infrastructure.language.generic import GenericAdapter
from bicho.infrastructure.language.registry import AdapterRegistry
from bicho.infrastructure.model.registry import ModelSpec, build_model_provider


class Container:
    """Builds a ``ReviewService`` from settings, caching the assembled service."""

    def __init__(
        self,
        settings: Settings,
        *,
        http: httpx.AsyncClient,
        clock: Clock | None = None,
        ids: IdGenerator | None = None,
    ) -> None:
        self._settings = settings
        self._http = http
        self._clock: Clock = clock or SystemClock()
        self._ids: IdGenerator = ids or UuidGenerator()
        self._service: ReviewService | None = None

    def review_service(self) -> ReviewService:
        """Return the shared, lazily-built review service."""
        if self._service is None:
            self._service = self._build_service()
        return self._service

    def _build_service(self) -> ReviewService:
        model = self._model_provider()
        analyzers = self._analyzers(model)
        return ReviewService(
            graph=build_graph(list(analyzers)),
            github=self._github(),
            diff_parser=DiffParser(),
            adapters=AdapterRegistry([], fallback=GenericAdapter()),
            analyzers=analyzers,
            ids=self._ids,
        )

    def _github(self) -> GitHubClient:
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
            installation_id=github.installation_id,
            http=self._http,
            api_base=github.api_base,
        )

    def _model_provider(self) -> ModelProvider:
        llm = self._settings.llm
        return build_model_provider(
            ModelSpec(
                model=llm.model,
                api_key=llm.api_key.get_secret_value(),
                base_url=llm.base_url,
                timeout_seconds=llm.timeout_seconds,
            )
        )

    def _analyzers(self, model: ModelProvider) -> Mapping[str, Analyzer]:
        return {"correctness": build_correctness_analyzer(model=model, ids=self._ids)}
