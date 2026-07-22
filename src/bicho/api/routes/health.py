"""Health, readiness, and version endpoints.

``/healthz`` is pure liveness — the process is up and serving, independent of configuration.
``/readyz`` reports whether required credentials are present, so a misconfigured deploy fails
visibly. ``/version`` exposes the app and workflow/prompt versions recorded in each review marker.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from bicho import __version__
from bicho.api.deps import get_settings
from bicho.application.graph.compose import WORKFLOW_VERSION
from bicho.application.prompts.registry import PROMPT_VERSION
from bicho.config.readiness import missing_requirements
from bicho.config.settings import Settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Response body for a liveness probe."""

    status: str


class VersionResponse(BaseModel):
    """Application and workflow/prompt versions."""

    version: str
    workflow_version: str
    prompt_version: str


@router.get("/healthz")
async def healthz() -> HealthResponse:
    """Liveness probe — the process is up and serving requests."""
    return HealthResponse(status="ok")


@router.get("/readyz")
async def readyz(settings: Annotated[Settings, Depends(get_settings)]) -> JSONResponse:
    """Readiness probe — 200 when required config is present, 503 (with details) otherwise."""
    problems = missing_requirements(settings)
    if problems:
        return JSONResponse(
            {"status": "not_ready", "problems": problems},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return JSONResponse({"status": "ready"}, status_code=status.HTTP_200_OK)


@router.get("/version")
async def version() -> VersionResponse:
    """Report the app version and the workflow/prompt versions stamped into review markers."""
    return VersionResponse(
        version=__version__,
        workflow_version=WORKFLOW_VERSION,
        prompt_version=PROMPT_VERSION,
    )
