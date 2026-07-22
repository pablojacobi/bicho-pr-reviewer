"""Tests for the hidden review marker."""

from bicho.domain.models.marker import ReviewMarker


def _marker() -> ReviewMarker:
    return ReviewMarker(
        head_sha="abc123",
        workflow_version="1.0",
        run_fingerprint="rf9",
        model_id="MiniMax-M3",
        prompt_version="v1",
    )


def test_marker_round_trips() -> None:
    assert ReviewMarker.parse(_marker().render()) == _marker()


def test_render_is_a_hidden_html_comment() -> None:
    rendered = _marker().render()

    assert rendered.startswith("<!--")
    assert rendered.endswith("-->")
    assert "bicho-pr-reviewer:1" in rendered


def test_parse_returns_none_without_a_marker() -> None:
    assert ReviewMarker.parse("just a normal review body") is None


def test_parse_finds_a_marker_inside_a_larger_body() -> None:
    body = f"## Summary\n\nSome findings...\n\n{_marker().render()}\n\nmore text"

    assert ReviewMarker.parse(body) == _marker()


def test_parse_returns_none_when_a_field_is_missing() -> None:
    assert ReviewMarker.parse("<!-- bicho-pr-reviewer:1 head_sha=abc -->") is None
