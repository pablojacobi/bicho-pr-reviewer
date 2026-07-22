"""A deterministic first-pass verification policy.

The full contextual (LLM) verifier is added later; for now this promotes confident findings to
CONFIRMED and rejects low-confidence ones, so only vetted findings reach composition.
"""

from bicho.domain.models.finding import Confidence, Finding, VerificationState


def verify(finding: Finding) -> Finding:
    """Return the finding with its verification state decided by the policy.

    Only ``CANDIDATE`` findings are judged here; a finding an earlier pass already resolved (e.g. a
    ``DUPLICATE`` from deduplication) is left untouched, so it is never promoted back to CONFIRMED.
    """
    if finding.verification_state is not VerificationState.CANDIDATE:
        return finding
    if finding.confidence is Confidence.LOW:
        return finding.model_copy(
            update={
                "verification_state": VerificationState.REJECTED,
                "verification_reason": "confidence below threshold for the first-pass policy",
            }
        )
    return finding.model_copy(
        update={
            "verification_state": VerificationState.CONFIRMED,
            "verification_reason": "confirmed by the first-pass policy",
        }
    )
