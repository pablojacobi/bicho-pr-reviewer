"""FastAPI dependency providers.

Dependencies pull already-wired collaborators off ``app.state`` (populated by the lifespan from the
:class:`Container`), so routes declare what they need without knowing how it is built.
"""

from fastapi import Request

from bicho.api.container import Container
from bicho.application.review_service import ReviewService


def get_review_service(request: Request) -> ReviewService:
    """Provide the shared review service assembled by the composition root."""
    container: Container = request.app.state.container
    return container.review_service()
