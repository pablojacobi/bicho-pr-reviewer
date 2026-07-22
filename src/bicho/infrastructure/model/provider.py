# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
"""A ``ModelProvider`` backed by a LangChain chat model.

Structured output is obtained via **function/tool calling** (not JSON mode): MiniMax's
OpenAI-compatible endpoint does not reliably honour ``response_format``. The model is bound to the
target schema as a tool and ``include_raw=True`` returns both the raw message and the parsed value,
so an invalid tool call surfaces as a ``parsing_error`` returned as data rather than raised.

The concrete chat model (``ChatOpenAI`` pointed at MiniMax) is injected, keeping this class free of
any provider-specific import; :mod:`bicho.infrastructure.model.registry` builds it from settings.
"""

import asyncio
from typing import Any, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from bicho.domain.ports.model_provider import ModelResult, RunMeta, error_result, ok_result


class LangChainModelProvider:
    """Runs a structured, schema-validated model call through an injected LangChain chat model."""

    def __init__(
        self,
        *,
        model: BaseChatModel,
        model_id: str,
        max_attempts: int = 1,
        retry_delay_seconds: float = 0.0,
        max_concurrency: int = 0,
    ) -> None:
        self._model = model
        self._model_id = model_id
        self._max_attempts = max(1, max_attempts)
        self._retry_delay_seconds = retry_delay_seconds
        # A shared semaphore serializes/bounds calls to this provider across the whole review; None
        # means unbounded (fully parallel). One instance is shared by every analyzer, so a limit of
        # 1 runs the LLM analyzers serially while the deterministic scanners still fan out.
        self._semaphore = asyncio.Semaphore(max_concurrency) if max_concurrency > 0 else None

    async def structured[T: BaseModel](
        self, *, prompt: str, schema: type[T], meta: RunMeta
    ) -> ModelResult[T]:
        if self._semaphore is None:
            return await self._with_retries(prompt=prompt, schema=schema, meta=meta)
        async with self._semaphore:
            return await self._with_retries(prompt=prompt, schema=schema, meta=meta)

    async def _with_retries[T: BaseModel](
        self, *, prompt: str, schema: type[T], meta: RunMeta
    ) -> ModelResult[T]:
        result = await self._attempt(prompt=prompt, schema=schema, meta=meta)
        attempt = 1
        while not result.ok and attempt < self._max_attempts:
            await asyncio.sleep(self._retry_delay_seconds)
            result = await self._attempt(prompt=prompt, schema=schema, meta=meta)
            attempt += 1
        return result

    async def _attempt[T: BaseModel](
        self, *, prompt: str, schema: type[T], meta: RunMeta
    ) -> ModelResult[T]:
        structured_model = self._model.with_structured_output(
            schema, method="function_calling", include_raw=True
        )
        try:
            response = await structured_model.ainvoke(prompt, config=_run_config(meta))
        except Exception as exc:  # transport/timeout errors are returned as data, never raised
            return error_result(f"{type(exc).__name__}: {exc}", model_id=self._model_id)

        # include_raw=True yields a {raw, parsed, parsing_error} mapping.
        result = cast(dict[str, Any], response)
        raw = _message_text(result.get("raw"))
        parsed = result.get("parsed")
        if parsed is None:
            reason = result.get("parsing_error") or "model returned no structured output"
            return error_result(str(reason), model_id=self._model_id, raw=raw)
        return ok_result(parsed, model_id=self._model_id, raw=raw)


def _run_config(meta: RunMeta) -> RunnableConfig:
    """Attach role/prompt/correlation tags so LangSmith records each call in context."""
    tags = [*meta.tags, f"role:{meta.role}", f"prompt:{meta.prompt_version}"]
    return {
        "run_name": meta.role,
        "tags": tags,
        "metadata": {"correlation_id": meta.correlation_id, "prompt_version": meta.prompt_version},
    }


def _message_text(message: object) -> str | None:
    """Best-effort textual content of the raw message, for tracing/the technical summary."""
    if isinstance(message, BaseMessage):
        return str(message.content)
    return None
