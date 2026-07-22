"""Tests for the analyzer registry: every role builds and has a prompt."""

from bicho.application.analyzers.base import LLMAnalyzer
from bicho.application.analyzers.registry import ANALYZER_CATEGORIES, build_analyzers
from bicho.application.prompts.registry import get_prompt
from bicho.infrastructure.model.fake import FakeModelProvider


class _Ids:
    def new_id(self) -> str:
        return "id"


def test_builds_an_analyzer_for_every_role_with_its_category() -> None:
    analyzers = build_analyzers(model=FakeModelProvider(), ids=_Ids())

    assert set(analyzers) == set(ANALYZER_CATEGORIES)
    for role, category in ANALYZER_CATEGORIES.items():
        analyzer = analyzers[role]
        assert isinstance(analyzer, LLMAnalyzer)
        assert analyzer._category is category


def test_every_role_has_a_prompt() -> None:
    for role in ANALYZER_CATEGORIES:
        assert get_prompt(role)
