"""FastAPI dependency providers.

Dependencies pull already-wired collaborators off ``app.state`` (populated by the lifespan), so
routes declare what they need without knowing how it is built — and tests can override any of them.
"""

from fastapi import Request

from bicho.api.background import BackgroundReviewRunner
from bicho.api.container import Container
from bicho.config.settings import Settings


def get_settings(request: Request) -> Settings:
    """Provide the application settings."""
    settings: Settings = request.app.state.settings
    return settings


def get_container(request: Request) -> Container:
    """Provide the composition root assembled by the lifespan."""
    container: Container = request.app.state.container
    return container


def get_review_runner(request: Request) -> BackgroundReviewRunner:
    """Provide the background review runner."""
    runner: BackgroundReviewRunner = request.app.state.review_runner
    return runner
