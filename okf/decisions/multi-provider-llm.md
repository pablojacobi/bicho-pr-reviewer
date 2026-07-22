---
type: Decision Record
title: Multi-provider LLM configuration
description: Configure several model providers at once and select the active one — no key swapping.
resource: https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/src/bicho/config/settings.py
tags: [decision, configuration, llm, providers]
timestamp: 2026-07-22T00:00:00Z
---

# Context

Adding a new model (e.g. Gemini) should not mean editing or replacing the one configured API key. All
candidate providers should be able to coexist, with an explicit selector.

# Decision

Configuration holds a **map of named providers**, each an OpenAI-compatible `ProviderSpec` (api_key,
base_url, model, timeout), plus an `active` selector. The composition root builds whichever provider is
active. Env shape:

```
BICHO_LLM__ACTIVE=minimax
BICHO_LLM__PROVIDERS__MINIMAX__API_KEY=…
BICHO_LLM__PROVIDERS__MINIMAX__BASE_URL=https://api.minimax.io/v1
BICHO_LLM__PROVIDERS__MINIMAX__MODEL=minimax-m3
# BICHO_LLM__PROVIDERS__GEMINI__…   ← add later, flip ACTIVE
```

# Consequences

Adding a model is a new provider block plus flipping `ACTIVE`, never swapping keys. The domain still
only sees the [ModelProvider port](model-provider-function-calling.md); this is purely configuration.
`/readyz` validates that the active provider is complete.

# Citations

[1] [settings.py](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/src/bicho/config/settings.py)
