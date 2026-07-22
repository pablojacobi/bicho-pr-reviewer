"""FastAPI application factory.

The app is built by a factory (rather than a module-level singleton) so tests can construct a fresh,
fully isolated instance and so future composition-root wiring (settings, ports, the compiled graph)
can be injected per instance.
"""

from fastapi import FastAPI

from bicho import __version__
from bicho.api.routes import health


def create_app() -> FastAPI:
    """Build and configure the Bicho PR Reviewer FastAPI application."""
    app = FastAPI(
        title="Bicho PR Reviewer",
        version=__version__,
        summary="Automated GitHub Pull Request review agent.",
    )
    app.include_router(health.router)
    return app
