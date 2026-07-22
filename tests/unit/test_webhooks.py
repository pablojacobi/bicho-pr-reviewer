"""Tests for the GitHub webhook route (signature, filtering, dedup, scheduling)."""

import hashlib
import hmac
import json
from typing import Any

import httpx
from pydantic import SecretStr

from bicho.api.app import create_app
from bicho.api.background import RecentDeliveries
from bicho.api.deps import get_review_runner
from bicho.config.settings import GitHubSettings, Settings
from bicho.domain.models.review import ReviewOptions, ReviewRequest

_SECRET = "s3cret"


class _SpyRunner:
    def __init__(self) -> None:
        self.scheduled: list[ReviewRequest] = []
        self.deliveries = RecentDeliveries()

    def schedule(self, request: ReviewRequest, options: ReviewOptions) -> None:
        self.scheduled.append(request)


def _payload(*, action: str = "opened", draft: bool = False) -> dict[str, Any]:
    return {
        "action": action,
        "pull_request": {"number": 1, "draft": draft, "head": {"sha": "sha"}},
        "repository": {"full_name": "o/r"},
        "installation": {"id": 42},
    }


def _sign(body: bytes) -> str:
    return "sha256=" + hmac.new(_SECRET.encode(), body, hashlib.sha256).hexdigest()


def _app_and_spy() -> tuple[Any, _SpyRunner]:
    app = create_app(Settings(github=GitHubSettings(webhook_secret=SecretStr(_SECRET))))
    spy = _SpyRunner()
    app.dependency_overrides[get_review_runner] = lambda: spy
    return app, spy


async def _post(app: Any, body: bytes, headers: dict[str, str]) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/webhooks/github", content=body, headers=headers)


def _headers(
    body: bytes, *, event: str = "pull_request", delivery: str | None = "d1"
) -> dict[str, str]:
    headers = {"X-Hub-Signature-256": _sign(body), "X-GitHub-Event": event}
    if delivery is not None:
        headers["X-GitHub-Delivery"] = delivery
    return headers


async def test_valid_event_schedules_a_review() -> None:
    app, spy = _app_and_spy()
    body = json.dumps(_payload()).encode()

    response = await _post(app, body, _headers(body))

    assert response.status_code == 202
    assert [request.repository for request in spy.scheduled] == ["o/r"]
    assert spy.scheduled[0].installation_id == 42


async def test_invalid_signature_is_rejected() -> None:
    app, spy = _app_and_spy()
    body = json.dumps(_payload()).encode()

    response = await _post(
        app, body, {"X-Hub-Signature-256": "sha256=bad", "X-GitHub-Event": "pull_request"}
    )

    assert response.status_code == 401
    assert spy.scheduled == []


async def test_non_pull_request_event_is_ignored() -> None:
    app, spy = _app_and_spy()
    body = json.dumps(_payload()).encode()

    response = await _post(app, body, _headers(body, event="ping"))

    assert response.status_code == 204
    assert spy.scheduled == []


async def test_uninteresting_action_is_ignored() -> None:
    app, spy = _app_and_spy()
    body = json.dumps(_payload(action="closed")).encode()

    response = await _post(app, body, _headers(body))

    assert response.status_code == 204
    assert spy.scheduled == []


async def test_draft_pull_request_is_ignored() -> None:
    app, spy = _app_and_spy()
    body = json.dumps(_payload(draft=True)).encode()

    response = await _post(app, body, _headers(body))

    assert response.status_code == 204
    assert spy.scheduled == []


async def test_duplicate_delivery_is_not_scheduled_twice() -> None:
    app, spy = _app_and_spy()
    spy.deliveries.register("d1")  # pretend we already handled delivery d1
    body = json.dumps(_payload()).encode()

    response = await _post(app, body, _headers(body, delivery="d1"))

    assert response.status_code == 202
    assert spy.scheduled == []


async def test_missing_delivery_header_still_schedules() -> None:
    app, spy = _app_and_spy()
    body = json.dumps(_payload()).encode()

    response = await _post(app, body, _headers(body, delivery=None))

    assert response.status_code == 202
    assert len(spy.scheduled) == 1
