"""Tests for the Environment enum."""

from bicho.config.environment import Environment


def test_environment_string_values() -> None:
    assert Environment.LOCAL == "local"
    assert Environment.TEST == "test"
    assert Environment.PRODUCTION == "production"


def test_is_production_true_only_for_production() -> None:
    assert Environment.PRODUCTION.is_production is True
    assert Environment.LOCAL.is_production is False
    assert Environment.TEST.is_production is False
