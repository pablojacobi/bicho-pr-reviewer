"""Tests for setting findings' inline-anchor flag against the diff."""

from collections.abc import Callable

from bicho.domain.models.diff import NormalizedDiff
from bicho.domain.models.finding import DiffSide, Finding
from bicho.domain.services.locations import anchor_findings

FindingFactory = Callable[..., Finding]


def test_keeps_inline_flag_for_an_anchorable_finding(
    make_finding: FindingFactory, sample_diff: NormalizedDiff
) -> None:
    finding = make_finding(
        path="app/db.py",
        start_line=11,
        end_line=12,
        diff_side=DiffSide.RIGHT,
        can_publish_inline=True,
    )

    (result,) = anchor_findings([finding], sample_diff)

    assert result.can_publish_inline is True


def test_disables_inline_flag_for_an_unanchorable_finding(
    make_finding: FindingFactory, sample_diff: NormalizedDiff
) -> None:
    finding = make_finding(
        path="app/db.py",
        start_line=99,
        end_line=99,
        diff_side=DiffSide.RIGHT,
        can_publish_inline=True,
    )

    (result,) = anchor_findings([finding], sample_diff)

    assert result.can_publish_inline is False
