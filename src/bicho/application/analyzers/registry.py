"""The analyzer registry: the roles Bicho runs and how to build them.

Each role maps to a finding :class:`Category` and shares the one :class:`LLMAnalyzer` implementation
(only the role's prompt differs). ``build_analyzers`` is the single place the composition root and
tests use to assemble the full set, so a new analyzer is added here and in the prompt registry.
"""

from collections.abc import Mapping

from bicho.application.analyzers.base import Analyzer, LLMAnalyzer
from bicho.domain.models.finding import Category
from bicho.domain.ports.model_provider import ModelProvider
from bicho.domain.ports.system import IdGenerator

ANALYZER_CATEGORIES: dict[str, Category] = {
    "correctness": Category.CORRECTNESS,
    "security": Category.SECURITY,
    "performance": Category.PERFORMANCE,
    "maintainability": Category.MAINTAINABILITY,
    "tests": Category.TESTS,
    "contracts": Category.CONTRACTS,
}


def build_analyzers(*, model: ModelProvider, ids: IdGenerator) -> Mapping[str, Analyzer]:
    """Build every analyzer, keyed by role name."""
    return {
        role: LLMAnalyzer(role=role, category=category, model=model, ids=ids)
        for role, category in ANALYZER_CATEGORIES.items()
    }
