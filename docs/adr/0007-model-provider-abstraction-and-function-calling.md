# 0007 — Model-provider abstraction and function-calling structured output

**Status:** Accepted

## Context

The reviewer depends on an LLM, but the domain and application layers must not depend on any specific
vendor. We also need the model to return *structured* findings we can validate, and MiniMax's
OpenAI-compatible endpoint does not reliably honour `response_format` (JSON mode) on M3.

## Decision

Reach the model only through a `ModelProvider` port (`domain/ports/model_provider.py`) whose one
method returns a `ModelResult[T]` — a validated Pydantic value **or an error, never a raised
exception**. The infrastructure implementation (`LangChainModelProvider`) obtains structured output
via **tool/function calling** (`with_structured_output(schema, method="function_calling",
include_raw=True)`), not JSON mode. A registry builds a MiniMax-pointed `ChatOpenAI`
(`temperature=0`, `max_retries=0`) from a `ModelSpec`; the model id and base URL are configuration.

## Consequences

- Nothing MiniMax-specific appears in code — swapping models is a config change, and the domain never
  imports `langchain_openai`.
- A malformed or refused tool call surfaces as a failed `ModelResult`, which the resilient graph nodes
  turn into a degraded outcome rather than crashing the parallel superstep
  ([ADR-0004](0004-single-container-in-process-background-tasks.md) topology).
- Each call is tagged with role / prompt version / correlation id for LangSmith tracing.
- **Trade-off:** function calling costs a little more prompt overhead than JSON mode, in exchange for
  reliability on M3 and provider portability.
