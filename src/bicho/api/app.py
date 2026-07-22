"""FastAPI application factory.

The app is built by a factory (rather than a module-level singleton) so tests can construct a fresh,
isolated instance with its own settings. The lifespan owns a single shared ``httpx`` client and
builds the :class:`Container` (the composition root) from settings, exposing it on ``app.state`` for
dependencies to read.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from bicho import __version__
from bicho.api.background import BackgroundReviewRunner
from bicho.api.container import Container
from bicho.api.routes import health, reviews, webhooks
from bicho.config.settings import Settings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings: Settings = app.state.settings
    async with httpx.AsyncClient() as http:
        container = Container(settings, http=http)
        runner = BackgroundReviewRunner(container)
        app.state.container = container
        app.state.review_runner = runner
        try:
            yield
        finally:
            await runner.drain()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the Bicho PR Reviewer FastAPI application."""
    app = FastAPI(
        title="Bicho PR Reviewer",
        version=__version__,
        summary="Automated GitHub Pull Request review agent.",
        lifespan=_lifespan,
    )
    app.state.settings = settings or Settings()
    app.include_router(health.router)
    app.include_router(reviews.router)
    app.include_router(webhooks.router)
    return app
