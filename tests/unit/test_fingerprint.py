"""Tests for stable finding fingerprints."""

from bicho.domain.services.fingerprint import compute_fingerprint


def _fp(
    path: str = "app/db.py",
    category: str = "security",
    subcategory: str = "sql-injection",
    rule_key: str = "sql-injection",
    enclosing_symbol: str | None = "get_user",
    snippet: str = "cursor.execute('SELECT * FROM u WHERE id=' + uid)",
) -> str:
    return compute_fingerprint(
        path=path,
        category=category,
        subcategory=subcategory,
        rule_key=rule_key,
        enclosing_symbol=enclosing_symbol,
        snippet=snippet,
    )


def test_fingerprint_is_16_hex_chars() -> None:
    fingerprint = _fp()

    assert len(fingerprint) == 16
    assert int(fingerprint, 16) >= 0


def test_fingerprint_is_deterministic() -> None:
    assert _fp() == _fp()


def test_fingerprint_is_stable_under_whitespace_changes() -> None:
    assert _fp() == _fp(snippet="  cursor.execute('SELECT * FROM u WHERE id=' + uid)\n\n  ")


def test_fingerprint_changes_with_rule_key() -> None:
    assert _fp() != _fp(rule_key="different-rule")


def test_fingerprint_ignores_leading_dot_slash_in_path() -> None:
    assert _fp() == _fp(path="./app/db.py")


def test_fingerprint_handles_missing_enclosing_symbol() -> None:
    assert len(_fp(enclosing_symbol=None)) == 16
