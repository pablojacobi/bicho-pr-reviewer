"""Property-based test: the review marker round-trips for any safe field values."""

import string

from hypothesis import given
from hypothesis import strategies as st

from bicho.domain.models.marker import ReviewMarker

# Marker field values in practice are SHAs, versions, and ids — no spaces or HTML delimiters.
_VALUE = st.text(alphabet=string.ascii_letters + string.digits + "-_.", min_size=1, max_size=40)


@given(head=_VALUE, workflow=_VALUE, run=_VALUE, model=_VALUE, prompt=_VALUE)
def test_marker_round_trips_for_any_safe_values(
    head: str, workflow: str, run: str, model: str, prompt: str
) -> None:
    marker = ReviewMarker(
        head_sha=head,
        workflow_version=workflow,
        run_fingerprint=run,
        model_id=model,
        prompt_version=prompt,
    )

    assert ReviewMarker.parse(marker.render()) == marker
