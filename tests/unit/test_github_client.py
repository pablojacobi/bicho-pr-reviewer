"""Tests for the httpx-backed GitHub client (RESPX-mocked, no network)."""

import json
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from bicho.domain.errors import PullRequestNotFoundError
from bicho.domain.models.finding import DiffSide
from bicho.domain.models.review import InlineComment, ReviewDraft, ReviewEvent
from bicho.infrastructure.github.auth import GitHubAppAuth
from bicho.infrastructure.github.client import GitHubClient, _next_page, _to_comment_payload

_API = "https://api.github.com"


def _generate_private_key() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


_PRIVATE_KEY = _generate_private_key()


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 7, 22, 12, 0, 0, tzinfo=UTC)


def _mock_token() -> None:
    respx.post(f"{_API}/app/installations/7/access_tokens").mock(
        return_value=httpx.Response(
            201, json={"token": "tok", "expires_at": "2026-07-22T13:00:00Z"}
        )
    )


def _client(http: httpx.AsyncClient) -> GitHubClient:
    auth = GitHubAppAuth(app_id="1", private_key=_PRIVATE_KEY, clock=_Clock(), http=http)
    return GitHubClient(auth=auth, installation_id=7, http=http)


@respx.mock
async def test_fetch_pull_request() -> None:
    _mock_token()
    respx.get(f"{_API}/repos/o/r/pulls/1").mock(
        return_value=httpx.Response(
            200,
            json={
                "number": 1,
                "title": "T",
                "body": "b",
                "draft": False,
                "head": {"sha": "sha"},
                "base": {"ref": "main", "repo": {"full_name": "o/r"}},
                "user": {"login": "alice"},
            },
        )
    )
    async with httpx.AsyncClient() as http:
        pull_request = await _client(http).fetch_pull_request("o/r", 1)

    assert pull_request.head_sha == "sha"
    assert pull_request.author == "alice"
    assert pull_request.installation_id == 7


@respx.mock
async def test_fetch_pull_request_not_found() -> None:
    _mock_token()
    respx.get(f"{_API}/repos/o/r/pulls/9").mock(return_value=httpx.Response(404, json={}))
    async with httpx.AsyncClient() as http:
        with pytest.raises(PullRequestNotFoundError):
            await _client(http).fetch_pull_request("o/r", 9)


@respx.mock
async def test_fetch_changed_files_follows_pagination() -> None:
    _mock_token()
    page_1 = httpx.Response(
        200,
        json=[{"filename": "a.py", "status": "modified", "patch": "@@"}],
        headers={"Link": f'<{_API}/repos/o/r/pulls/1/files?page=2>; rel="next"'},
    )
    page_2 = httpx.Response(200, json=[{"filename": "b.py", "status": "added", "patch": None}])
    respx.get(url__startswith=f"{_API}/repos/o/r/pulls/1/files").mock(side_effect=[page_1, page_2])
    async with httpx.AsyncClient() as http:
        files = await _client(http).fetch_changed_files("o/r", 1)

    assert [file.filename for file in files] == ["a.py", "b.py"]


@respx.mock
async def test_list_reviews() -> None:
    _mock_token()
    respx.get(f"{_API}/repos/o/r/pulls/1/reviews").mock(
        return_value=httpx.Response(
            200, json=[{"id": 5, "user": {"login": "bicho[bot]"}, "body": "<!-- marker -->"}]
        )
    )
    async with httpx.AsyncClient() as http:
        reviews = await _client(http).list_reviews("o/r", 1)

    assert reviews[0].id == 5
    assert reviews[0].author == "bicho[bot]"


@respx.mock
async def test_publish_review_sends_the_payload() -> None:
    _mock_token()
    captured: dict[str, Any] = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["json"] = json.loads(request.content)
        return httpx.Response(200, json={"id": 999})

    respx.post(f"{_API}/repos/o/r/pulls/1/reviews").mock(side_effect=_capture)
    draft = ReviewDraft(
        summary="s",
        event=ReviewEvent.COMMENT,
        commit_id="sha",
        inline_comments=(
            InlineComment(path="a.py", line=12, body="b", start_line=10, start_side=DiffSide.RIGHT),
        ),
    )
    async with httpx.AsyncClient() as http:
        review_id = await _client(http).publish_review("o/r", 1, draft)

    assert review_id == 999
    assert captured["json"]["commit_id"] == "sha"
    assert captured["json"]["comments"][0]["start_line"] == 10


@respx.mock
async def test_publish_review_without_comments() -> None:
    _mock_token()
    captured: dict[str, Any] = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["json"] = json.loads(request.content)
        return httpx.Response(200, json={"id": 1})

    respx.post(f"{_API}/repos/o/r/pulls/1/reviews").mock(side_effect=_capture)
    draft = ReviewDraft(summary="s", event=ReviewEvent.COMMENT, commit_id="sha")
    async with httpx.AsyncClient() as http:
        await _client(http).publish_review("o/r", 1, draft)

    assert "comments" not in captured["json"]


@respx.mock
async def test_fetch_file_content_returns_text() -> None:
    _mock_token()
    respx.get(url__startswith=f"{_API}/repos/o/r/contents/app/db.py").mock(
        return_value=httpx.Response(200, text="print('hi')\n")
    )
    async with httpx.AsyncClient() as http:
        content = await _client(http).fetch_file_content("o/r", "app/db.py", "sha")

    assert content == "print('hi')\n"


async def test_fetch_file_content_rejects_unsafe_path() -> None:
    async with httpx.AsyncClient() as http:
        assert await _client(http).fetch_file_content("o/r", "../etc/passwd", "sha") is None


@respx.mock
async def test_fetch_file_content_missing_is_none() -> None:
    _mock_token()
    respx.get(url__startswith=f"{_API}/repos/o/r/contents/gone.py").mock(
        return_value=httpx.Response(404, json={})
    )
    async with httpx.AsyncClient() as http:
        assert await _client(http).fetch_file_content("o/r", "gone.py", "sha") is None


@respx.mock
async def test_fetch_file_content_skips_oversized() -> None:
    _mock_token()
    respx.get(url__startswith=f"{_API}/repos/o/r/contents/big.py").mock(
        return_value=httpx.Response(200, content=b"x" * 1_000_001)
    )
    async with httpx.AsyncClient() as http:
        assert await _client(http).fetch_file_content("o/r", "big.py", "sha") is None


@respx.mock
async def test_fetch_file_content_skips_binary() -> None:
    _mock_token()
    respx.get(url__startswith=f"{_API}/repos/o/r/contents/logo.png").mock(
        return_value=httpx.Response(200, content=b"\x00\x01\x02")
    )
    async with httpx.AsyncClient() as http:
        assert await _client(http).fetch_file_content("o/r", "logo.png", "sha") is None


@respx.mock
async def test_fetch_file_content_skips_undecodable() -> None:
    _mock_token()
    respx.get(url__startswith=f"{_API}/repos/o/r/contents/weird.py").mock(
        return_value=httpx.Response(200, content=b"\xff\xfe")
    )
    async with httpx.AsyncClient() as http:
        assert await _client(http).fetch_file_content("o/r", "weird.py", "sha") is None


def test_next_page_parsing() -> None:
    assert _next_page(None) is None
    assert _next_page('<https://x/2>; rel="next"') == "https://x/2"
    assert _next_page('<https://x/1>; rel="prev"') is None
    assert _next_page("<https://x/1>") is None


def test_comment_payload_single_line_has_no_start() -> None:
    payload = _to_comment_payload(InlineComment(path="a.py", line=10, body="b"))

    assert "start_line" not in payload


def test_comment_payload_multiline_defaults_start_side_to_side() -> None:
    payload = _to_comment_payload(InlineComment(path="a.py", line=12, body="b", start_line=10))

    assert payload["start_line"] == 10
    assert payload["start_side"] == "RIGHT"
