"""Finding verification: decide which candidate findings are real before they are composed.

Two implementations behind one protocol. ``PolicyVerifier`` is the deterministic first pass: it
confirms confident findings and rejects low-confidence ones (no model). ``LLMFindingVerifier`` adds
a single **batched** model call that judges every candidate finding against the diff to cut false
positives; if that call fails it falls back to the policy, so it never makes a review worse than the
deterministic pass. Findings an earlier stage already resolved (e.g. ``DUPLICATE``) pass through
untouched.
"""

from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel

from bicho.application.analyzers.base import render_diff
from bicho.application.prompts.registry import PROMPT_VERSION, get_prompt
from bicho.domain.models.diff import NormalizedDiff
from bicho.domain.models.finding import Finding, VerificationState
from bicho.domain.ports.model_provider import ModelProvider, RunMeta
from bicho.domain.services.verification_policy import verify as policy_verify


class FindingVerdict(BaseModel):
    """The verifier's decision on one candidate finding, referenced by its index."""

    index: int
    keep: bool
    reason: str = ""


class VerificationReport(BaseModel):
    """The verifier model's structured output: one verdict per judged finding."""

    verdicts: tuple[FindingVerdict, ...] = ()


class FindingVerifier(Protocol):
    """Decides the verification state of each finding."""

    async def verify(
        self, findings: Sequence[Finding], *, diff: NormalizedDiff, correlation_id: str
    ) -> list[Finding]: ...


class PolicyVerifier:
    """The deterministic confidence policy, applied to each candidate finding."""

    async def verify(
        self, findings: Sequence[Finding], *, diff: NormalizedDiff, correlation_id: str
    ) -> list[Finding]:
        return [policy_verify(finding) for finding in findings]


class LLMFindingVerifier:
    """Judges candidate findings with one batched model call, falling back to the policy."""

    def __init__(self, *, model: ModelProvider) -> None:
        self._model = model

    async def verify(
        self, findings: Sequence[Finding], *, diff: NormalizedDiff, correlation_id: str
    ) -> list[Finding]:
        candidates = [
            index
            for index, finding in enumerate(findings)
            if finding.verification_state is VerificationState.CANDIDATE
        ]
        if not candidates:
            return list(findings)
        meta = RunMeta(
            role="verifier", prompt_version=PROMPT_VERSION, correlation_id=correlation_id
        )
        result = await self._model.structured(
            prompt=_render_prompt(diff, findings, candidates),
            schema=VerificationReport,
            meta=meta,
        )
        if not result.ok or result.value is None:
            return [_policy_if_candidate(finding) for finding in findings]
        verdicts = {verdict.index: verdict for verdict in result.value.verdicts}
        return [_apply(index, finding, verdicts) for index, finding in enumerate(findings)]


def _policy_if_candidate(finding: Finding) -> Finding:
    if finding.verification_state is VerificationState.CANDIDATE:
        return policy_verify(finding)
    return finding


def _apply(index: int, finding: Finding, verdicts: dict[int, FindingVerdict]) -> Finding:
    if finding.verification_state is not VerificationState.CANDIDATE:
        return finding
    verdict = verdicts.get(index)
    if verdict is None:
        return policy_verify(finding)
    if verdict.keep:
        return finding.model_copy(
            update={
                "verification_state": VerificationState.CONFIRMED,
                "verification_reason": verdict.reason or "confirmed by the verifier",
            }
        )
    return finding.model_copy(
        update={
            "verification_state": VerificationState.REJECTED,
            "verification_reason": verdict.reason or "rejected by the verifier",
        }
    )


def _render_prompt(
    diff: NormalizedDiff, findings: Sequence[Finding], candidates: Sequence[int]
) -> str:
    lines = [get_prompt("verifier"), "", "## Diff", render_diff(diff), "", "## Candidate findings"]
    for index in candidates:
        finding = findings[index]
        lines.append(
            f"[{index}] ({finding.category.value}/{finding.severity.value}) "
            f"{finding.path}:{finding.start_line} — {finding.title}: {finding.explanation}"
        )
    return "\n".join(lines)
