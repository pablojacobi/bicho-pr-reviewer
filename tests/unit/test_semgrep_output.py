"""Tests for parsing Semgrep JSON output."""

from bicho.infrastructure.scanners.semgrep_output import SemgrepOutput


def test_defaults_to_no_results() -> None:
    assert SemgrepOutput().results == []


def test_result_extra_defaults_and_ignores_unknown_keys() -> None:
    output = SemgrepOutput.model_validate(
        {
            "extra_top_level_key": "ignored",
            "results": [
                {"check_id": "r", "path": "a.py", "start": {"line": 3}, "end": {"line": 3}}
            ],
        }
    )

    result = output.results[0]
    assert result.extra.severity == "INFO"
    assert result.extra.message == ""
