"""Port for reading a pull request and publishing a review on GitHub."""

from typing import Protocol

from bicho.domain.models.pull_request import ChangedFile, PullRequest
from bicho.domain.models.review import ExistingReview, ReviewDraft


class GitHubPort(Protocol):
    """Reads PR metadata, files, and reviews, and publishes a single review."""

    async def fetch_pull_request(self, repository: str, number: int) -> PullRequest: ...

    async def fetch_changed_files(
        self, repository: str, number: int
    ) -> tuple[ChangedFile, ...]: ...

    async def list_reviews(self, repository: str, number: int) -> tuple[ExistingReview, ...]: ...

    async def publish_review(self, repository: str, number: int, draft: ReviewDraft) -> int: ...
