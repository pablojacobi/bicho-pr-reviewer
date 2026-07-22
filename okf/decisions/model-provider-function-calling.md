---
type: Decision Record
title: Model-provider abstraction and function-calling output
description: Reach the LLM only through a port; get structured output via tool calling; errors are data.
resource: https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/adr/0007-model-provider-abstraction-and-function-calling.md
tags: [decision, llm, function-calling, provider-abstraction]
timestamp: 2026-07-22T00:00:00Z
---

# Context

The reviewer depends on an LLM, but the domain must not depend on any vendor, and it needs *structured*
findings it can validate. MiniMax's OpenAI-compatible endpoint does not reliably honour JSON mode on M3.

# Decision

Reach the model only through a `ModelProvider` port whose one method returns a `ModelResult[T]` — a
validated value or an error, **never a raised exception**. The infrastructure implementation obtains
structured output via **tool/function calling** (not JSON mode) and validates against a Pydantic
schema. A registry builds an OpenAI-compatible chat model from configuration.

# Consequences

Nothing vendor-specific appears in code — swapping models is configuration (see
[multi-provider LLM](multi-provider-llm.md)). A malformed or refused tool call becomes a degraded
outcome the [resilient pipeline](../review-pipeline.md) tolerates, and each call is tagged for
LangSmith tracing.

# Citations

[1] [ADR-0007](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/docs/adr/0007-model-provider-abstraction-and-function-calling.md)
