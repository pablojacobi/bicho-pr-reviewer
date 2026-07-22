"""Port for structured LLM calls.

The domain and application layers reach models only through this port, so they never import
provider-specific classes. A call returns a ``ModelResult`` — a parse failure or transport error is
returned as data, not raised — which the resilient graph nodes turn into a degraded outcome.
"""

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict


class RunMeta(BaseModel):
    """Metadata attached to a model call for tracing (LangSmith) and the technical summary."""

    model_config = ConfigDict(frozen=True)

    role: str
    prompt_version: str
    correlation_id: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModelResult[T: BaseModel]:
    """The outcome of a structured model call: a validated value, or an error (never raised)."""

    ok: bool
    model_id: str
    value: T | None = None
    raw: str | None = None
    error: str | None = None


def ok_result[T: BaseModel](value: T, *, model_id: str, raw: str | None = None) -> ModelResult[T]:
    """Build a successful, validated model result."""
    return ModelResult(ok=True, model_id=model_id, value=value, raw=raw)


def error_result(error: str, *, model_id: str, raw: str | None = None) -> ModelResult[Any]:
    """Build a failed model result (transport error, or invalid/unparseable output)."""
    return ModelResult[Any](ok=False, model_id=model_id, error=error, raw=raw)


class ModelProvider(Protocol):
    """Executes a structured, schema-validated model call."""

    async def structured[T: BaseModel](
        self, *, prompt: str, schema: type[T], meta: RunMeta
    ) -> ModelResult[T]: ...
