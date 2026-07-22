"""An httpx-backed ``GitHubPort`` using a GitHub App installation token.

Constructed per installation: every request carries a fresh-enough installation token from
``GitHubAppAuth``. Reads the PR, its changed files (paginated), and existing reviews; publishes one
review with inline comments (``commit_id`` pinned to the analyzed head SHA).
"""

from typing import Any

import httpx

from bicho.domain.errors import PullRequestNotFoundError
from bicho.domain.models.pull_request import ChangedFile, PullRequest
from bicho.domain.models.review import ExistingReview, InlineComment, ReviewDraft
from bicho.infrastructure.fs.pathsafe import (
    is_probably_binary,
    is_safe_relative_path,
    is_within_size,
)
from bicho.infrastructure.github.auth import GitHubAppAuth

_ACCEPT = "application/vnd.github+json"
_RAW_ACCEPT = "application/vnd.github.raw+json"
_API_VERSION = "2022-11-28"
_HTTP_NOT_FOUND = 404


class GitHubClient:
    """Reads PRs/files/reviews and publishes a review, authenticated per installation."""

    def __init__(
        self,
        *,
        auth: GitHubAppAuth,
        installation_id: int,
        http: httpx.AsyncClient,
        api_base: str = "https://api.github.com",
    ) -> None:
        self._auth = auth
        self._installation_id = installation_id
        self._http = http
        self._api_base = api_base.rstrip("/")

    async def _headers(self) -> dict[str, str]:
        token = await self._auth.installation_token(self._installation_id)
        return {
            "Authorization": f"Bearer {token}",
            "Accept": _ACCEPT,
            "X-GitHub-Api-Version": _API_VERSION,
        }

    async def fetch_pull_request(self, repository: str, number: int) -> PullRequest:
        response = await self._http.get(
            f"{self._api_base}/repos/{repository}/pulls/{number}", headers=await self._headers()
        )
        if response.status_code == _HTTP_NOT_FOUND:
            raise PullRequestNotFoundError(f"{repository}#{number}")
        response.raise_for_status()
        return _to_pull_request(response.json(), self._installation_id)

    async def fetch_changed_files(self, repository: str, number: int) -> tuple[ChangedFile, ...]:
        files: list[ChangedFile] = []
        url: str | None = f"{self._api_base}/repos/{repository}/pulls/{number}/files?per_page=100"
        while url is not None:
            response = await self._http.get(url, headers=await self._headers())
            response.raise_for_status()
            files.extend(_to_changed_file(item) for item in response.json())
            url = _next_page(response.headers.get("Link"))
        return tuple(files)

    async def fetch_file_content(self, repository: str, path: str, ref: str) -> str | None:
        if not is_safe_relative_path(path):
            return None
        response = await self._http.get(
            f"{self._api_base}/repos/{repository}/contents/{path}",
            params={"ref": ref},
            headers={**await self._headers(), "Accept": _RAW_ACCEPT},
        )
        if response.status_code == _HTTP_NOT_FOUND:
            return None
        response.raise_for_status()
        data = response.content
        if not is_within_size(len(data)) or is_probably_binary(data):
            return None
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return None

    async def list_reviews(self, repository: str, number: int) -> tuple[ExistingReview, ...]:
        response = await self._http.get(
            f"{self._api_base}/repos/{repository}/pulls/{number}/reviews",
            headers=await self._headers(),
        )
        response.raise_for_status()
        return tuple(_to_existing_review(item) for item in response.json())

    async def publish_review(self, repository: str, number: int, draft: ReviewDraft) -> int:
        response = await self._http.post(
            f"{self._api_base}/repos/{repository}/pulls/{number}/reviews",
            headers=await self._headers(),
            json=_to_review_payload(draft),
        )
        response.raise_for_status()
        return int(response.json()["id"])


def _to_pull_request(data: dict[str, Any], installation_id: int) -> PullRequest:
    user: dict[str, Any] = data.get("user") or {}
    return PullRequest(
        repository=data["base"]["repo"]["full_name"],
        number=data["number"],
        head_sha=data["head"]["sha"],
        base_ref=data["base"]["ref"],
        title=data["title"],
        body=data.get("body") or "",
        is_draft=bool(data.get("draft", False)),
        author=user.get("login", ""),
        installation_id=installation_id,
    )


def _to_changed_file(data: dict[str, Any]) -> ChangedFile:
    return ChangedFile(
        filename=data["filename"],
        status=data["status"],
        patch=data.get("patch"),
        previous_filename=data.get("previous_filename"),
        additions=data.get("additions", 0),
        deletions=data.get("deletions", 0),
    )


def _to_existing_review(data: dict[str, Any]) -> ExistingReview:
    user: dict[str, Any] = data.get("user") or {}
    return ExistingReview(id=data["id"], author=user.get("login", ""), body=data.get("body") or "")


def _to_review_payload(draft: ReviewDraft) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "commit_id": draft.commit_id,
        "body": draft.summary,
        "event": draft.event.value,
    }
    comments = [_to_comment_payload(comment) for comment in draft.inline_comments]
    if comments:
        payload["comments"] = comments
    return payload


def _to_comment_payload(comment: InlineComment) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "path": comment.path,
        "line": comment.line,
        "side": comment.side.value,
        "body": comment.body,
    }
    if comment.start_line is not None:
        payload["start_line"] = comment.start_line
        payload["start_side"] = (comment.start_side or comment.side).value
    return payload


def _next_page(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        segments = part.split(";")
        if len(segments) >= 2 and 'rel="next"' in segments[1]:
            return segments[0].strip().strip("<>")
    return None
