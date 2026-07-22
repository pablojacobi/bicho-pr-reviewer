"""Review request, options, and the composed review draft."""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from bicho.domain.models.finding import Category, DiffSide


class ReviewTrigger(StrEnum):
    """What triggered a review."""

    WEBHOOK = "webhook"
    MANUAL = "manual"


class ReviewEvent(StrEnum):
    """The GitHub review event to submit (Bicho uses COMMENT or REQUEST_CHANGES, never APPROVE)."""

    COMMENT = "COMMENT"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    APPROVE = "APPROVE"


class ReviewOptions(BaseModel):
    """Per-review options, identical for the webhook and manual paths."""

    model_config = ConfigDict(frozen=True)

    dry_run: bool = False
    force: bool = False
    focus: str | None = None
    categories: tuple[Category, ...] = ()


class ReviewRequest(BaseModel):
    """The input to a review: which PR to review and why."""

    model_config = ConfigDict(frozen=True)

    repository: str
    pr_number: int
    installation_id: int | None = None
    head_sha_hint: str | None = None
    trigger: ReviewTrigger = ReviewTrigger.MANUAL


class InlineComment(BaseModel):
    """A single inline comment to place on the diff."""

    model_config = ConfigDict(frozen=True)

    path: str
    line: int
    body: str
    side: DiffSide = DiffSide.RIGHT
    start_line: int | None = None
    start_side: DiffSide | None = None

    @model_validator(mode="after")
    def _validate_range(self) -> Self:
        if self.start_line is not None and self.start_line > self.line:
            raise ValueError("start_line must be less than or equal to line")
        return self

    @property
    def is_multiline(self) -> bool:
        """Whether this comment spans more than one line."""
        return self.start_line is not None


class ReviewDraft(BaseModel):
    """The composed review: a summary, an event, and inline comments, anchored to a commit."""

    model_config = ConfigDict(frozen=True)

    summary: str
    event: ReviewEvent
    commit_id: str
    inline_comments: tuple[InlineComment, ...] = ()
