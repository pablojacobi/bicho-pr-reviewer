"""Pull request metadata."""

from pydantic import BaseModel, ConfigDict


class PullRequest(BaseModel):
    """The metadata Bicho needs about a pull request; its diff is a separate ``NormalizedDiff``."""

    model_config = ConfigDict(frozen=True)

    repository: str
    number: int
    head_sha: str
    base_ref: str
    title: str
    body: str = ""
    is_draft: bool = False
    author: str = ""
    installation_id: int | None = None
