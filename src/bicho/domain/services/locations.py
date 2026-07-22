"""Set each finding's inline-anchor flag against the diff.

A confirmed finding that cannot be anchored to a commentable diff line is not dropped — it is routed
to the review summary instead (see ``Finding.publish_in_summary``). This service only decides, per
finding, whether an inline anchor is possible.
"""

from collections.abc import Sequence

from bicho.domain.models.diff import NormalizedDiff
from bicho.domain.models.finding import Finding
from bicho.domain.services.diff_mapping import can_anchor


def anchor_findings(findings: Sequence[Finding], diff: NormalizedDiff) -> list[Finding]:
    """Return the findings with ``can_publish_inline`` set to whether each anchors to the diff."""
    result: list[Finding] = []
    for finding in findings:
        anchorable = can_anchor(
            diff,
            path=finding.path,
            start_line=finding.start_line,
            end_line=finding.end_line,
            side=finding.diff_side,
        )
        if finding.can_publish_inline == anchorable:
            result.append(finding)
        else:
            result.append(finding.model_copy(update={"can_publish_inline": anchorable}))
    return result
