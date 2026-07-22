"""The hidden review marker used for idempotency.

Bicho embeds one hidden HTML comment in each review it publishes. Before reviewing again, it reads
the existing reviews and parses this marker to check whether the current head SHA and workflow
version were already reviewed. GitHub is the source of truth; there is no database.
"""

import re

from pydantic import BaseModel, ConfigDict

_MARKER_PREFIX = "bicho-pr-reviewer"
_MARKER_VERSION = "1"
_MARKER_RE = re.compile(
    rf"<!--\s*{re.escape(_MARKER_PREFIX)}:{re.escape(_MARKER_VERSION)}\s+(?P<fields>.*?)\s*-->",
    re.DOTALL,
)
_FIELD_RE = re.compile(r"(\w+)=(\S*)")


class ReviewMarker(BaseModel):
    """Identifies a review Bicho published, so a re-run can detect it without any storage."""

    model_config = ConfigDict(frozen=True)

    head_sha: str
    workflow_version: str
    run_fingerprint: str
    model_id: str
    prompt_version: str

    def render(self) -> str:
        """Render the marker as a hidden HTML comment to embed in a review body."""
        fields = " ".join(
            [
                f"head_sha={self.head_sha}",
                f"workflow_version={self.workflow_version}",
                f"run={self.run_fingerprint}",
                f"model={self.model_id}",
                f"prompt={self.prompt_version}",
            ]
        )
        return f"<!-- {_MARKER_PREFIX}:{_MARKER_VERSION} {fields} -->"

    @classmethod
    def parse(cls, text: str) -> ReviewMarker | None:
        """Extract a marker from ``text`` (e.g. a review body), or ``None`` if absent/incomplete."""
        match = _MARKER_RE.search(text)
        if match is None:
            return None
        fields = dict(_FIELD_RE.findall(match.group("fields")))
        try:
            return cls(
                head_sha=fields["head_sha"],
                workflow_version=fields["workflow_version"],
                run_fingerprint=fields["run"],
                model_id=fields["model"],
                prompt_version=fields["prompt"],
            )
        except KeyError:
            return None
