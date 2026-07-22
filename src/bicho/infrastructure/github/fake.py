"""A configurable ``GitHubPort`` fake for tests and offline runs.

Pre-load it with a pull request, changed files, and existing reviews. It records published reviews
and hands out incrementing review ids, so the pipeline runs end-to-end without hitting GitHub.
"""

from collections.abc import Mapping, Sequence

from bicho.domain.errors import PullRequestNotFoundError
from bicho.domain.models.pull_request import ChangedFile, PullRequest
from bicho.domain.models.review import ExistingReview, ReviewDraft


class FakeGitHub:
    """An in-memory ``GitHubPort`` implementation."""

    def __init__(
        self,
        *,
        pull_request: PullRequest | None = None,
        changed_files: Sequence[ChangedFile] = (),
        reviews: Sequence[ExistingReview] = (),
        file_contents: Mapping[str, str] | None = None,
        moved_head_sha: str | None = None,
    ) -> None:
        self._pull_request = pull_request
        self._changed_files = tuple(changed_files)
        self._reviews = tuple(reviews)
        self._file_contents = dict(file_contents or {})
        # When set, the second and later fetches report this head SHA, simulating a push that
        # lands between analysis and publishing (exercises the stale-head guard).
        self._moved_head_sha = moved_head_sha
        self._fetch_count = 0
        self.published: list[ReviewDraft] = []
        self._next_review_id = 1000

    async def fetch_pull_request(self, repository: str, number: int) -> PullRequest:
        if self._pull_request is None:
            raise PullRequestNotFoundError(f"{repository}#{number}")
        self._fetch_count += 1
        if self._moved_head_sha is not None and self._fetch_count > 1:
            return self._pull_request.model_copy(update={"head_sha": self._moved_head_sha})
        return self._pull_request

    async def fetch_changed_files(self, repository: str, number: int) -> tuple[ChangedFile, ...]:
        return self._changed_files

    async def fetch_file_content(self, repository: str, path: str, ref: str) -> str | None:
        return self._file_contents.get(path)

    async def list_reviews(self, repository: str, number: int) -> tuple[ExistingReview, ...]:
        return self._reviews

    async def publish_review(self, repository: str, number: int, draft: ReviewDraft) -> int:
        self.published.append(draft)
        review_id = self._next_review_id
        self._next_review_id += 1
        return review_id
