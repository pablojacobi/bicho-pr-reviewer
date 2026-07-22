---
type: Reference
title: Configuration
description: Typed settings read from BICHO_-prefixed environment variables, with nested sections.
resource: https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/.env.example
tags: [operations, configuration, environment, settings]
timestamp: 2026-07-22T00:00:00Z
---

# How settings load

All environment access lives in a typed, validated `Settings` object. Variables use the `BICHO_`
prefix; nested sections use a `__` (double-underscore) delimiter — e.g. `BICHO_GITHUB__APP_ID` maps to
`settings.github.app_id`. Secrets are `SecretStr` and scrubbed from logs.

# Sections

- **GitHub** (`BICHO_GITHUB__*`): `APP_ID`, `PRIVATE_KEY`, `INSTALLATION_ID`, `WEBHOOK_SECRET`,
  `API_BASE`. The private key may be supplied as a single line with literal `\n` between PEM lines
  (Railway and `.env` are single-line); Bicho restores the newlines.
- **LLM** (`BICHO_LLM__*`): an `ACTIVE` selector plus a map of named providers —
  `BICHO_LLM__PROVIDERS__<NAME>__{API_KEY,BASE_URL,MODEL,TIMEOUT_SECONDS}`. See
  [multi-provider LLM](../decisions/multi-provider-llm.md).
- **Scanner** (`BICHO_SCANNER__*`): `SEMGREP_ENABLED`, `SEMGREP_CONFIG`, `PIP_AUDIT_ENABLED`, and
  timeouts. Optional — see [deterministic scanners](../decisions/deterministic-scanners.md).
- **LangSmith** (`LANGSMITH_*`, read directly by LangChain): `TRACING`, `API_KEY`, `PROJECT`.

# Readiness

`GET /readyz` returns 200 when the required configuration (GitHub App fields and a complete active LLM
provider) is present, or 503 with the list of what is missing. `GET /healthz` is pure liveness;
`GET /version` reports the app, workflow, and prompt versions.

# Citations

[1] [.env.example](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/.env.example)
