"""Tests for the PullRequest model."""

from bicho.domain.models.pull_request import PullRequest


def test_pull_request_construction_and_defaults() -> None:
    pr = PullRequest(repository="owner/repo", number=7, head_sha="abc", base_ref="main", title="T")

    assert pr.repository == "owner/repo"
    assert pr.number == 7
    assert pr.body == ""
    assert pr.is_draft is False
    assert pr.installation_id is None
