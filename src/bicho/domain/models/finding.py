"""The normalized Finding — the single shape every scanner and analyzer produces.

A finding carries everything needed to verify it, deduplicate it, decide whether it can be
published, and render it as a GitHub review comment. Only findings in the ``CONFIRMED`` state are
ever published; the publish-gate logic lives here so composition never re-derives it.
"""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Category(StrEnum):
    """Top-level finding category (drives analyzer routing and grouping)."""

    CORRECTNESS = "correctness"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    TESTS = "tests"
    CONTRACTS = "contracts"
    DEPENDENCY = "dependency"


class Severity(StrEnum):
    """Finding severity, ordered by :attr:`rank` (higher is more severe)."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        """A total order over severities, used when merging and prioritizing findings."""
        return _SEVERITY_RANK[self]


_SEVERITY_RANK = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


class Confidence(StrEnum):
    """How confident we are that a finding is real (adjusted by the verifier)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DiffSide(StrEnum):
    """Which side of the diff a location refers to, in GitHub's terms."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"


class SourceKind(StrEnum):
    """What produced a finding."""

    LLM_ANALYZER = "llm_analyzer"
    SEMGREP = "semgrep"
    PIP_AUDIT = "pip_audit"


class VerificationState(StrEnum):
    """A finding's lifecycle state; only ``CONFIRMED`` findings are published."""

    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"
    NEEDS_CONTEXT = "needs_context"
    OUT_OF_SCOPE = "out_of_scope"
    CANNOT_ANCHOR = "cannot_anchor"
    STALE = "stale"


class EvidenceRef(BaseModel):
    """A pointer to supporting evidence (a caller, a schema, a test, a scanner hit)."""

    model_config = ConfigDict(frozen=True)

    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    detail: str


class Finding(BaseModel):
    """A single, normalized review finding produced by a scanner or analyzer."""

    model_config = ConfigDict(frozen=True)

    id: str
    fingerprint: str
    category: Category
    subcategory: str
    severity: Severity
    confidence: Confidence
    title: str
    explanation: str
    impact: str
    recommendation: str
    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    diff_side: DiffSide = DiffSide.RIGHT
    snippet: str = ""
    evidence: tuple[EvidenceRef, ...] = ()
    source_kind: SourceKind
    source_name: str
    verification_state: VerificationState = VerificationState.CANDIDATE
    verification_reason: str | None = None
    head_sha: str
    prompt_version: str | None = None
    model_id: str | None = None
    language: str
    framework: str | None = None
    can_publish_inline: bool = True
    summary_only: bool = False

    @model_validator(mode="after")
    def _validate_line_range(self) -> Self:
        if self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")
        return self

    @property
    def is_confirmed(self) -> bool:
        """Whether this finding passed verification and may be published at all."""
        return self.verification_state is VerificationState.CONFIRMED

    @property
    def publish_inline(self) -> bool:
        """Whether to publish this finding as an inline comment on the diff."""
        return self.is_confirmed and self.can_publish_inline and not self.summary_only

    @property
    def publish_in_summary(self) -> bool:
        """Whether to publish this finding in the review summary instead of inline."""
        return self.is_confirmed and (self.summary_only or not self.can_publish_inline)
