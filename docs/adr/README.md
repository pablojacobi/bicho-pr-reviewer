# Architecture Decision Records

Lightweight records of significant, hard-to-reverse decisions and their rationale. Each ADR is
immutable once **Accepted**; a later ADR may **supersede** an earlier one rather than editing it.

Format: **Context** (the forces), **Decision** (what we chose), **Consequences** (the trade-offs).

| #                                                                | Decision                                                   |
| ---------------------------------------------------------------- | ---------------------------------------------------------- |
| [0001](0001-use-architecture-decision-records.md)                | Use Architecture Decision Records                          |
| [0002](0002-start-clean-from-template.md)                        | Start clean from the FastAPI/LangGraph template            |
| [0003](0003-no-database-github-as-source-of-truth.md)            | No database — GitHub is the source of truth                |
| [0004](0004-single-container-in-process-background-tasks.md)     | Single container, in-process background tasks              |
| [0005](0005-one-hundred-percent-coverage-and-tdd.md)             | 100% coverage and TDD                                      |
| [0006](0006-language-agnostic-core-with-adapters.md)             | Language-agnostic core with adapters                       |
| [0007](0007-model-provider-abstraction-and-function-calling.md)  | Model-provider abstraction + function-calling output       |
| [0008](0008-one-review-idempotency-marker-and-stale-head-guard.md) | One review per run: idempotency marker + stale-head guard |
| [0009](0009-deterministic-scanners-semgrep-and-pip-audit.md)     | Deterministic scanners: Semgrep CE and pip-audit           |
