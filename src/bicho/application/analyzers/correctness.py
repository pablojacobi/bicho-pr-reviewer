"""The correctness-and-reliability analyzer."""

from bicho.application.analyzers.base import LLMAnalyzer
from bicho.domain.models.finding import Category
from bicho.domain.ports.model_provider import ModelProvider
from bicho.domain.ports.system import IdGenerator


def build_correctness_analyzer(*, model: ModelProvider, ids: IdGenerator) -> LLMAnalyzer:
    """Build the correctness-and-reliability analyzer."""
    return LLMAnalyzer(role="correctness", category=Category.CORRECTNESS, model=model, ids=ids)
