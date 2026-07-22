"""Tests for the review request/options/draft models."""

import pytest
from pydantic import ValidationError

from bicho.domain.models.finding import Category, DiffSide
from bicho.domain.models.review import (
    InlineComment,
    ReviewDraft,
    ReviewEvent,
    ReviewOptions,
    ReviewRequest,
    ReviewTrigger,
)


def test_review_options_defaults() -> None:
    options = ReviewOptions()

    assert options.dry_run is False
    assert options.force is False
    assert options.focus is None
    assert options.categories == ()


def test_review_options_accept_categories() -> None:
    assert ReviewOptions(categories=(Category.SECURITY,)).categories == (Category.SECURITY,)


def test_review_request_defaults_to_manual_trigger() -> None:
    assert ReviewRequest(repository="o/r", pr_number=1).trigger is ReviewTrigger.MANUAL


def test_single_line_comment_is_not_multiline() -> None:
    comment = InlineComment(path="a.py", line=10, body="b")

    assert comment.is_multiline is False
    assert comment.side is DiffSide.RIGHT


def test_multiline_comment_is_multiline() -> None:
    comment = InlineComment(
        path="a.py", line=12, body="b", start_line=10, start_side=DiffSide.RIGHT
    )

    assert comment.is_multiline is True


def test_inline_comment_rejects_start_line_after_line() -> None:
    with pytest.raises(ValidationError):
        InlineComment(path="a.py", line=5, body="b", start_line=10)


def test_review_draft_holds_event_and_comments() -> None:
    comment = InlineComment(path="a.py", line=1, body="b")
    draft = ReviewDraft(
        summary="s", event=ReviewEvent.REQUEST_CHANGES, commit_id="sha", inline_comments=(comment,)
    )

    assert draft.event is ReviewEvent.REQUEST_CHANGES
    assert draft.inline_comments == (comment,)
