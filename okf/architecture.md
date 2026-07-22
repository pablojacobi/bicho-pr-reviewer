---
type: Architecture
title: Architecture and the dependency rule
description: Layered hexagonal design with all side effects behind injectable ports.
resource: https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/ARCHITECTURE.md
tags: [architecture, hexagonal, ports-and-adapters, layering]
timestamp: 2026-07-22T00:00:00Z
---

# Layers

Bicho is a single stateless container with no database — GitHub itself is the source of truth for what
has already been reviewed. The code follows a strict dependency rule:

```
api → application → domain ← infrastructure
```

- **domain** — framework-free core: models (`PullRequest`, `NormalizedDiff`, `Finding`,
  `ReviewDraft`, `ReviewMarker`, `AnalyzerOutcome`), ports (Protocols), and pure services
  (fingerprint, dedup, diff-mapping, anchoring, verification). Imports nothing framework-specific.
- **application** — the `ReviewService` use case and the LangGraph workflow, plus the six LLM
  analyzers behind a shared `LLMAnalyzer`. `langgraph`/`langchain` live only here.
- **infrastructure** — adapters implementing the ports: the GitHub client + App auth, the LangChain
  model provider, the diff hunk parser, the Semgrep and pip-audit scanners, the language adapters,
  and the system seams. `langchain_openai`, `httpx`, `semgrep`, `pip-audit`, and `ast` live only here.
- **api** — the FastAPI app + lifespan (owns the shared `httpx` client and builds the composition
  root), `POST /reviews`, `POST /webhooks/github`, the background runner, and health/readiness.

# Injected seams

Everything with a side effect sits behind a **port** (a `Protocol` in `domain/ports/`) with an
injectable implementation: Clock, IdGenerator, SubprocessRunner, TempWorkspace, GitHubPort,
ModelProvider, DiffParserPort, LanguageAdapter. Wall-clock, randomness, subprocess, filesystem, and
network are never touched outside `infrastructure`. This is what makes the entire test suite
deterministic and 100%-coverable offline — no credentials, no network, no real services.

# One graph, two entrypoints

The manual endpoint and the webhook run the **same** compiled graph via `ReviewService.run`; the only
difference is the `ReviewOptions` (`dry_run` / `force` / `focus` / `categories`) and the trigger. There
is no duplicated orchestration.

# Related

* [Review pipeline](review-pipeline.md) — the graph topology and its load-bearing invariant.
* [Language-agnostic core](decisions/language-agnostic-core.md) — the adapter contract.
* [No database, GitHub as source of truth](decisions/no-database.md).

# Citations

[1] [ARCHITECTURE.md](https://github.com/pablojacobi/bicho-pr-reviewer/blob/main/ARCHITECTURE.md)
