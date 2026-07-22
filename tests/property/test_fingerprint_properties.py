"""Property-based tests for finding fingerprints."""

from hypothesis import given
from hypothesis import strategies as st

from bicho.domain.services.fingerprint import compute_fingerprint

_HEX = set("0123456789abcdef")
# Real inputs are UTF-8 text; constrain the generator to encodable characters (no lone surrogates).
_TEXT = st.text(st.characters(codec="utf-8"))


@given(
    path=_TEXT,
    category=_TEXT,
    subcategory=_TEXT,
    rule_key=_TEXT,
    symbol=_TEXT,
    snippet=_TEXT,
)
def test_fingerprint_is_deterministic_16_char_hex(
    path: str, category: str, subcategory: str, rule_key: str, symbol: str, snippet: str
) -> None:
    def compute() -> str:
        return compute_fingerprint(
            path=path,
            category=category,
            subcategory=subcategory,
            rule_key=rule_key,
            enclosing_symbol=symbol,
            snippet=snippet,
        )

    fingerprint = compute()

    assert fingerprint == compute()
    assert len(fingerprint) == 16
    assert set(fingerprint) <= _HEX


@given(snippet=_TEXT, padding=st.sampled_from(["", " ", "\t", "\n", "  \n\t "]))
def test_fingerprint_is_stable_under_surrounding_whitespace(snippet: str, padding: str) -> None:
    bare = compute_fingerprint(
        path="p",
        category="c",
        subcategory="s",
        rule_key="r",
        enclosing_symbol=None,
        snippet=snippet,
    )
    padded = compute_fingerprint(
        path="p",
        category="c",
        subcategory="s",
        rule_key="r",
        enclosing_symbol=None,
        snippet=f"{padding}{snippet}{padding}",
    )

    assert bare == padded
