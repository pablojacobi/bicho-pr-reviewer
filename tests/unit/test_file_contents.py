"""Tests for gathering in-scope file contents and the generic adapter's scope rules."""

from bicho.application.graph.nodes import _collect_contents
from bicho.domain.models.pull_request import ChangedFile, PullRequest
from bicho.infrastructure.github.fake import FakeGitHub
from bicho.infrastructure.language.generic import GenericAdapter


def _pr() -> PullRequest:
    return PullRequest(repository="o/r", number=1, head_sha="sha", base_ref="main", title="T")


def _changed(filename: str, *, patch: str | None = "@@") -> ChangedFile:
    return ChangedFile(filename=filename, status="modified", patch=patch)


def test_generic_adapter_scope_excludes_binary_generated_and_unsafe() -> None:
    adapter = GenericAdapter()

    assert adapter.in_scope(_changed("app/db.py")) is True
    assert adapter.in_scope(_changed("logo.png", patch=None)) is False
    assert adapter.in_scope(_changed("node_modules/x.js")) is False
    assert adapter.in_scope(_changed("../evil.py")) is False


async def test_collect_contents_fetches_only_in_scope_files_with_content() -> None:
    github = FakeGitHub(file_contents={"app/ok.py": "code", "app/present.py": "more"})
    changed = (
        _changed("app/ok.py"),  # in scope, content -> included
        _changed("app/missing.py"),  # in scope, no content on server -> skipped
        _changed("dist/bundle.js"),  # generated -> skipped
        _changed("assets/logo.png", patch=None),  # no patch -> skipped
    )

    contents = await _collect_contents(github, _pr(), GenericAdapter(), changed)

    assert contents == {"app/ok.py": "code"}
