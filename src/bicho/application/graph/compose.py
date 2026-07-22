"""Compose a single ``ReviewDraft`` from verified findings.

Only CONFIRMED findings are published. Each is anchored to the diff: anchorable ones become inline
comments, the rest are listed in the summary. A hidden marker is embedded for idempotency.
"""

import hashlib
from collections.abc import Sequence

from bicho.application.prompts.registry import PROMPT_VERSION
from bicho.domain.models.analysis import AnalyzerOutcome
from bicho.domain.models.diff import NormalizedDiff
from bicho.domain.models.finding import Finding
from bicho.domain.models.marker import ReviewMarker
from bicho.domain.models.pull_request import PullRequest
from bicho.domain.models.review import InlineComment, ReviewDraft
from bicho.domain.services.locations import anchor_findings
from bicho.domain.services.severity_policy import review_event

WORKFLOW_VERSION = "1"


def compose_review_draft(
    *,
    findings: Sequence[Finding],
    diff: NormalizedDiff,
    pull_request: PullRequest,
    outcomes: Sequence[AnalyzerOutcome],
) -> ReviewDraft:
    """Assemble the review: inline comments for anchorable findings, the rest in the summary."""
    confirmed = anchor_findings([f for f in findings if f.is_confirmed], diff)
    inline = tuple(_to_comment(f) for f in confirmed if f.publish_inline)
    summary_only = [f for f in confirmed if f.publish_in_summary]
    marker = ReviewMarker(
        head_sha=pull_request.head_sha,
        workflow_version=WORKFLOW_VERSION,
        run_fingerprint=_run_fingerprint(pull_request.head_sha),
        model_id=_model_id(confirmed),
        prompt_version=PROMPT_VERSION,
    )
    return ReviewDraft(
        summary=_render_summary(confirmed, summary_only, outcomes, marker),
        event=review_event(confirmed),
        commit_id=pull_request.head_sha,
        inline_comments=inline,
    )


def _to_comment(finding: Finding) -> InlineComment:
    multiline = finding.start_line != finding.end_line
    return InlineComment(
        path=finding.path,
        line=finding.end_line,
        side=finding.diff_side,
        body=_comment_body(finding),
        start_line=finding.start_line if multiline else None,
        start_side=finding.diff_side if multiline else None,
    )


def _comment_body(finding: Finding) -> str:
    return (
        f"**[{finding.category.value} · {finding.severity.value}]** {finding.title}\n\n"
        f"{finding.explanation}\n\n"
        f"**Impact:** {finding.impact}\n\n"
        f"**Recommendation:** {finding.recommendation}"
    )


def _render_summary(
    confirmed: Sequence[Finding],
    summary_only: Sequence[Finding],
    outcomes: Sequence[AnalyzerOutcome],
    marker: ReviewMarker,
) -> str:
    lines = ["## Bicho PR Review", ""]
    lines.append(
        f"{len(confirmed)} confirmed finding(s)." if confirmed else "No confirmed issues found."
    )
    if summary_only:
        lines += ["", "### Findings not anchorable to the diff"]
        lines += [f"- `{f.path}:{f.start_line}` — {f.title}" for f in summary_only]
    degraded = [outcome for outcome in outcomes if outcome.degraded]
    if degraded:
        lines += ["", "### Analysis notes"]
        lines += [
            f"- {diag.source}: {diag.status.value} — {diag.message}"
            for outcome in degraded
            for diag in outcome.diagnostics
        ]
    lines += ["", marker.render()]
    return "\n".join(lines)


def _model_id(findings: Sequence[Finding]) -> str:
    for finding in findings:
        if finding.model_id is not None:
            return finding.model_id
    return "none"


def _run_fingerprint(head_sha: str) -> str:
    payload = f"{head_sha}\x1f{WORKFLOW_VERSION}\x1f{PROMPT_VERSION}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
