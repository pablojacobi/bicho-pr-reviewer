"""Tests for the FakeGitHub adapter and the GitHubPort contract."""

import pytest

from bicho.domain.errors import PullRequestNotFoundError
from bicho.domain.models.pull_request import ChangedFile, PullRequest
from bicho.domain.models.review import ExistingReview, ReviewDraft, ReviewEvent
from bicho.domain.ports.github import GitHubPort
from bicho.infrastructure.github.fake import FakeGitHub


def _pr() -> PullRequest:
    return PullRequest(
        repository="owner/repo", number=1, head_sha="sha", base_ref="main", title="T"
    )


async def test_fetch_pull_request_returns_the_configured_pr() -> None:
    github: GitHubPort = FakeGitHub(pull_request=_pr())

    pull_request = await github.fetch_pull_request("owner/repo", 1)

    assert pull_request.number == 1


async def test_fetch_pull_request_raises_when_absent() -> None:
    github = FakeGitHub()

    with pytest.raises(PullRequestNotFoundError):
        await github.fetch_pull_request("owner/repo", 1)


async def test_fetch_changed_files() -> None:
    files = (ChangedFile(filename="a.py", status="modified", patch="@@ -1 +1 @@\n-a\n+b\n"),)
    github = FakeGitHub(pull_request=_pr(), changed_files=files)

    assert await github.fetch_changed_files("owner/repo", 1) == files


async def test_list_reviews() -> None:
    reviews = (ExistingReview(id=5, author="bicho[bot]", body="<!-- marker -->"),)
    github = FakeGitHub(pull_request=_pr(), reviews=reviews)

    assert await github.list_reviews("owner/repo", 1) == reviews


async def test_publish_review_records_the_draft_and_returns_an_id() -> None:
    github = FakeGitHub(pull_request=_pr())
    draft = ReviewDraft(summary="s", event=ReviewEvent.COMMENT, commit_id="sha")

    review_id = await github.publish_review("owner/repo", 1, draft)

    assert isinstance(review_id, int)
    assert github.published == [draft]
