# Architecture Decisions

The significant, hard-to-reverse decisions that shaped Bicho, each as an OKF concept mirroring the
canonical [ADRs](https://github.com/pablojacobi/bicho-pr-reviewer/tree/main/docs/adr).

* [Start clean from the template](template-reuse.md) — borrow structure, copy no code.
* [No database — GitHub as source of truth](no-database.md).
* [Single container, in-process background tasks](single-container-background-tasks.md).
* [100% coverage and TDD](full-coverage-tdd.md).
* [Language-agnostic core with adapters](language-agnostic-core.md).
* [Model-provider abstraction + function calling](model-provider-function-calling.md).
* [Multi-provider LLM configuration](multi-provider-llm.md).
* [One review: idempotency marker + stale-head guard](one-review-idempotency-stale-guard.md).
* [Deterministic scanners: Semgrep CE and pip-audit](deterministic-scanners.md).
