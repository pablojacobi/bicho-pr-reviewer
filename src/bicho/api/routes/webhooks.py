"""GitHub webhook endpoint.

Verifies the HMAC signature over the raw body *before* parsing, filters to reviewable
``pull_request`` actions, de-duplicates redeliveries, then schedules the review off-request and
returns 202 at once. The heavy work (LangGraph, the model, publishing) never runs in the request.
"""

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status

from bicho.api.background import BackgroundReviewRunner
from bicho.api.deps import get_review_runner, get_settings
from bicho.api.security import verify_signature
from bicho.config.settings import Settings
from bicho.domain.models.review import ReviewOptions, ReviewRequest, ReviewTrigger

router = APIRouter(tags=["webhooks"])

_EVENT = "pull_request"
_ACTIONS = frozenset({"opened", "synchronize", "reopened", "ready_for_review"})


@router.post("/webhooks/github", summary="Receive a GitHub webhook")
async def github_webhook(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    runner: Annotated[BackgroundReviewRunner, Depends(get_review_runner)],
    x_hub_signature_256: Annotated[str | None, Header()] = None,
    x_github_event: Annotated[str | None, Header()] = None,
    x_github_delivery: Annotated[str | None, Header()] = None,
) -> Response:
    """Acknowledge a webhook and schedule a review for reviewable pull-request events."""
    body = await request.body()
    secret = settings.github.webhook_secret.get_secret_value()
    if not verify_signature(secret, body, x_hub_signature_256):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid signature")

    if x_github_event != _EVENT:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    payload: dict[str, Any] = json.loads(body)
    pull_request = payload.get("pull_request", {})
    if payload.get("action") not in _ACTIONS or pull_request.get("draft", False):
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if x_github_delivery is not None and not runner.deliveries.register(x_github_delivery):
        return Response(status_code=status.HTTP_202_ACCEPTED)

    runner.schedule(
        ReviewRequest(
            repository=payload["repository"]["full_name"],
            pr_number=pull_request["number"],
            installation_id=payload["installation"]["id"],
            head_sha_hint=pull_request["head"]["sha"],
            trigger=ReviewTrigger.WEBHOOK,
        ),
        ReviewOptions(),
    )
    return Response(status_code=status.HTTP_202_ACCEPTED)
