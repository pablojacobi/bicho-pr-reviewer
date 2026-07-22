"""Manual review endpoint.

``POST /reviews`` runs the same ``ReviewService.run`` as the webhook path. With ``dry_run`` (the
default) it returns the composed draft — summary plus the inline comments that *would* be posted —
without touching GitHub, so the pipeline can be exercised end to end from curl or Swagger before any
credentials or live publishing exist.
"""

from typing import Annotated, Self

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from bicho.api.container import Container
from bicho.api.deps import get_container
from bicho.domain.models.finding import Category
from bicho.domain.models.review import (
    ReviewDraft,
    ReviewOptions,
    ReviewRequest,
    ReviewResult,
    ReviewStatus,
    ReviewTrigger,
)

router = APIRouter(tags=["reviews"])


class ReviewRequestBody(BaseModel):
    """Request body for a manual review."""

    repository: str = Field(examples=["octo/hello-world"])
    pr_number: int = Field(ge=1, examples=[42])
    installation_id: int | None = None
    dry_run: bool = True
    force: bool = False
    focus: str | None = None
    categories: tuple[Category, ...] = ()


class ReviewResultResponse(BaseModel):
    """The outcome of a review run."""

    status: ReviewStatus
    confirmed_count: int
    total_count: int
    draft: ReviewDraft | None = None
    review_id: int | None = None

    @classmethod
    def of(cls, result: ReviewResult) -> Self:
        """Project a domain ``ReviewResult`` onto the API response."""
        return cls(
            status=result.status,
            confirmed_count=result.confirmed_count,
            total_count=result.total_count,
            draft=result.draft,
            review_id=result.review_id,
        )


@router.post("/reviews", summary="Run a review for a pull request")
async def create_review(
    body: ReviewRequestBody,
    container: Annotated[Container, Depends(get_container)],
) -> ReviewResultResponse:
    """Run the review pipeline for one pull request and return the result (dry-run by default)."""
    request = ReviewRequest(
        repository=body.repository,
        pr_number=body.pr_number,
        installation_id=body.installation_id,
        trigger=ReviewTrigger.MANUAL,
    )
    options = ReviewOptions(
        dry_run=body.dry_run,
        force=body.force,
        focus=body.focus,
        categories=body.categories,
    )
    result = await container.review_service(body.installation_id).run(request, options)
    return ReviewResultResponse.of(result)
