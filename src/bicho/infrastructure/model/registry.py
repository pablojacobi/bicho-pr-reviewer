"""Builds the concrete chat model and provider from configuration.

MiniMax is reached through its OpenAI-compatible endpoint, so ``ChatOpenAI`` is the transport: the
model id and base URL are configuration, never hard-coded, and nothing here is MiniMax-specific in
code. ``temperature=0`` and ``max_retries=0`` keep runs deterministic and bound latency; retries and
fallback are handled explicitly by the graph, not silently by the client.
"""

from dataclasses import dataclass

from langchain_openai import ChatOpenAI

from bicho.infrastructure.model.provider import LangChainModelProvider


@dataclass(frozen=True)
class ModelSpec:
    """Everything needed to construct a chat model for one role."""

    model: str
    api_key: str
    base_url: str
    timeout_seconds: float = 60.0


def build_chat_model(spec: ModelSpec) -> ChatOpenAI:
    """Construct a ``ChatOpenAI`` pointed at an OpenAI-compatible endpoint (e.g. MiniMax)."""
    return ChatOpenAI(
        model=spec.model,
        api_key=spec.api_key,  # pyright: ignore[reportArgumentType] — str is accepted at runtime
        base_url=spec.base_url,
        timeout=spec.timeout_seconds,
        temperature=0.0,
        max_retries=0,
    )


def build_model_provider(spec: ModelSpec) -> LangChainModelProvider:
    """Construct the structured-output provider for a role."""
    return LangChainModelProvider(model=build_chat_model(spec), model_id=spec.model)
