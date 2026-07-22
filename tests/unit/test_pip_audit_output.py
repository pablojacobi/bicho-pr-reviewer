"""Tests for parsing pip-audit JSON output."""

from bicho.infrastructure.scanners.pip_audit_output import PipAuditOutput


def test_defaults_to_no_dependencies() -> None:
    assert PipAuditOutput().dependencies == []


def test_parses_dependency_defaults_and_ignores_unknown_keys() -> None:
    output = PipAuditOutput.model_validate(
        {"fixes": [], "dependencies": [{"name": "flask", "extra_key": "ignored"}]}
    )

    dependency = output.dependencies[0]
    assert dependency.version == ""
    assert dependency.vulns == []
