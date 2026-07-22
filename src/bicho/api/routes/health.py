"""Health endpoints.

``/healthz`` is a pure liveness probe: it confirms the process is up and serving without touching
any external dependency. Readiness (``/readyz``), which validates required configuration and the
availability of the Semgrep executable, is added in a later phase.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Response body for a health probe."""

    status: str


@router.get("/healthz")
async def healthz() -> HealthResponse:
    """Liveness probe — the process is up and serving requests."""
    return HealthResponse(status="ok")
