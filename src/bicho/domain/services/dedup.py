"""Deduplication of findings that share a fingerprint.

Findings with the same fingerprint describe the same issue, possibly surfaced by different sources
(e.g. Semgrep and an LLM analyzer). We keep one survivor — enriched with the others' evidence and,
when corroborated by an independent source, a raised confidence — and mark the rest ``DUPLICATE``
(retained for logging, never published). The result is deterministic regardless of input order.
"""

from collections import defaultdict
from collections.abc import Sequence

from bicho.domain.models.finding import (
    Confidence,
    EvidenceRef,
    Finding,
    SourceKind,
    VerificationState,
)

_CONFIDENCE_ORDER = [Confidence.LOW, Confidence.MEDIUM, Confidence.HIGH]
_CONFIDENCE_RANK = {confidence: rank for rank, confidence in enumerate(_CONFIDENCE_ORDER)}
_SOURCE_PRIORITY = {
    SourceKind.SEMGREP: 2,
    SourceKind.PIP_AUDIT: 1,
    SourceKind.LLM_ANALYZER: 0,
}


def deduplicate(findings: Sequence[Finding]) -> list[Finding]:
    """Merge same-fingerprint findings: enriched survivors plus losers marked ``DUPLICATE``."""
    groups: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        groups[finding.fingerprint].append(finding)

    result: list[Finding] = []
    for group in groups.values():
        if len(group) == 1:
            result.append(group[0])
            continue
        survivor = _select_survivor(group)
        losers = [finding for finding in group if finding.id != survivor.id]
        result.append(_enrich(survivor, losers))
        result.extend(_mark_duplicate(loser, survivor) for loser in losers)
    return result


def _select_survivor(group: Sequence[Finding]) -> Finding:
    # Best = highest severity, then confidence, then source priority; ties broken by lowest id.
    ordered = sorted(
        group,
        key=lambda finding: (
            -finding.severity.rank,
            -_CONFIDENCE_RANK[finding.confidence],
            -_SOURCE_PRIORITY[finding.source_kind],
            finding.id,
        ),
    )
    return ordered[0]


def _enrich(survivor: Finding, losers: Sequence[Finding]) -> Finding:
    group = (survivor, *losers)
    max_severity = max(group, key=lambda finding: finding.severity.rank).severity
    corroborated = any(loser.source_kind != survivor.source_kind for loser in losers)
    confidence = _raise_confidence(survivor.confidence) if corroborated else survivor.confidence
    return survivor.model_copy(
        update={
            "evidence": _merge_evidence(group),
            "severity": max_severity,
            "confidence": confidence,
        }
    )


def _merge_evidence(findings: Sequence[Finding]) -> tuple[EvidenceRef, ...]:
    seen: dict[EvidenceRef, None] = {}
    for finding in findings:
        for reference in finding.evidence:
            seen[reference] = None
    return tuple(seen)


def _raise_confidence(confidence: Confidence) -> Confidence:
    index = min(_CONFIDENCE_RANK[confidence] + 1, len(_CONFIDENCE_ORDER) - 1)
    return _CONFIDENCE_ORDER[index]


def _mark_duplicate(loser: Finding, survivor: Finding) -> Finding:
    return loser.model_copy(
        update={
            "verification_state": VerificationState.DUPLICATE,
            "verification_reason": f"merged into {survivor.id}",
        }
    )
